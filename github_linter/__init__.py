""" goes through your repos and checks for things """

from collections import deque

from datetime import datetime
import os
import time
from types import ModuleType
from typing import Any, Dict, Optional, List, Tuple, Union

import json5 as json
from loguru import logger
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
import pytz

from .repolinter import RepoLinter
from .utils import load_config


__version__ = "0.0.1"


RATELIMIT_TYPES = {
    "core": {
        "minlimit": 50,
    },
    "graphql": {
        "minlimit": 5,
    },
    "search": {
        "minlimit": 1,
    },
}


class GithubLinter:
    """ does things """

    def __init__(self):
        """ setup """
        self.config = load_config()
        if not self.config:
            self.config = {}

        self.do_login()

        self.current_repo: Optional[Repository] = None
        self.report = {}
        self.modules: Dict[str, ModuleType] = {}
        self.filecache: Dict[str, Dict[str, Optional[ContentFile]]] = {}

    def do_login(self) -> None:
        """ does the login/auth bit """

        if "github" not in self.config:
            if os.getenv("GITHUB_TOKEN"):
                logger.debug("Using GITHUB_TOKEN environment variable for login.")
                self.github = Github(os.getenv("GITHUB_TOKEN"))
        else:
            if "github" not in self.config:
                raise ValueError(
                    "No 'github' key in config, and no GITHUB_TOKEN auth - cannot start up."
                )
            if (
                "ignore_auth" in self.config["github"]
                and self.config["github"]["ignore_auth"]
            ):
                self.github = Github()
            elif (
                "username" not in self.config["github"]
                or "password" not in self.config["github"]
            ):
                raise ValueError(
                    "No authentication details available - cannot start up."
                )
            else:
                self.github = Github(
                    login_or_token=self.config["github"]["username"],
                    password=self.config["github"]["password"],
                )

    def add_module(self, module_name: str, module: ModuleType):
        """ adds a module to modules """
        self.modules[module_name] = module

    def check_rate_limits(self) -> int:
        """ checks the rate limits and returns a number of seconds to wait """
        rate_limits = self.github.get_rate_limit()
        logger.debug(json.dumps(rate_limits, indent=4, default=str, ensure_ascii=False))
        sleep_time = 0

        for rate_type in RATELIMIT_TYPES:
            if hasattr(rate_limits, rate_type):
                remaining = getattr(rate_limits, rate_type).remaining
                reset = getattr(rate_limits, rate_type).reset.astimezone(pytz.utc)
                if RATELIMIT_TYPES[rate_type]["minlimit"] >= remaining:
                    logger.debug("Need to wait until {}", reset)
                    now = datetime.now(tz=pytz.utc)
                    wait_time = reset - now
                    logger.debug(wait_time)
                    if wait_time.seconds > 300:
                        logger.error(
                            "You're going to need to wait a long time for the {} rate limit to reset... {} seconds.",
                            reset,
                            now,
                            wait_time.seconds,
                        )
                    if wait_time.seconds > sleep_time:
                        sleep_time = wait_time.seconds
                else:
                    logger.debug(
                        "Rate limit for {} is {}, {} remaining - resets {}",
                        rate_type,
                        getattr(rate_limits, rate_type).limit,
                        remaining,
                        reset,
                    )
        return sleep_time

    def display_report(self):
        """ displays a report """
        for repo_name in self.report:
            repo = self.report[repo_name]
            if not repo:
                logger.warning("Empty report for {}, skipping", repo_name)
            errors = []
            warnings = []
            fixes = []
            if "errors" in repo and repo["errors"]:
                for category in repo["errors"]:
                    deque(
                        map(
                            errors.append,
                            [
                                f"{category} - {error}"
                                for error in repo["errors"].get(category)
                            ],
                        )
                    )
            if "warnings" in repo and repo["warnings"]:
                for category in repo["warnings"]:
                    deque(
                        map(
                            warnings.append,
                            [
                                f"{category} - {warning}"
                                for warning in repo["warnings"].get(category)
                            ],
                        )
                    )
            if "fixes" in repo and repo["fixes"]:
                for category in repo["fixes"]:
                    deque(
                        map(
                            fixes.append,
                            [
                                f"{category} - {fix}"
                                for fix in repo["fixes"].get(category)
                            ],
                        )
                    )
            if errors or warnings or fixes:
                logger.info("Report for {}", repo_name)
                # deque forces map to just run
                deque(map(logger.error, errors))
                deque(map(logger.warning, warnings))
                deque(map(logger.info, fixes))
            else:
                logger.info("Repository {} checks out OK", repo_name)

    def handle_repo(
        self,
        repo: Repository,
        check: Optional[Tuple],
        fix: bool,
    ):
        """ Runs modules against the given repo """

        repolinter = RepoLinter(repo)
        self.current_repo = repolinter.repository

        logger.debug("Current repo: {}", repo.full_name)
        if repolinter.repository.archived:
            logger.warning(
                "Repository {} is archived!", repolinter.repository.full_name
            )

        if repolinter.repository.parent:
            logger.warning("Parent: {}", repolinter.repository.parent.full_name)

        logger.debug("Enabled modules: {}", self.modules)
        for module in self.modules:
            repolinter.run_module(
                module=self.modules[module],
                check_filter=check,
                do_fixes=fix,
            )

        if not repolinter.errors or repolinter.warnings:
            logger.debug("{} all good", repolinter.repository.full_name)
        self.report[repolinter.repository.full_name] = {
            "errors": repolinter.errors,
            "warnings": repolinter.warnings,
            "fixes": repolinter.fixes,
        }

        time.sleep(self.check_rate_limits())


def get_all_user_repos(github: GithubLinter) -> List[Repository]:
    """ simpler filtered listing """
    config = load_config()

    logger.debug("Pulling all repositories accessible to user.")
    repolist = list(github.github.get_user().get_repos())
    if config["linter"]["owner_list"]:
        logger.debug(
            "Filtering by owner list in linter config: {}",
            ",".join(config["linter"]["owner_list"]),
        )
        return [
            repo
            for repo in repolist
            if repo.owner.login in config["linter"]["owner_list"]
        ]
    return repolist


def search_repos(
    github: GithubLinter, kwargs_object: Dict[str, Dict[Any, Any]]
) -> List[Repository]:
    """ search repos based on cli input """

    config = load_config()

    if "repo" in kwargs_object or "owner" in kwargs_object:
        search = ""
        searchrepos = []
        if "repo" in kwargs_object:
            for repo in kwargs_object["repo"]:
                if "owner" in kwargs_object:
                    for owner in kwargs_object["owner"]:
                        searchrepos.append(f"{owner}/{repo}")
                else:
                    searchrepos.append(repo)
        else:
            logger.warning("Filtering on owner alone")
            searchrepos = [f"user:{owner}" for owner in kwargs_object["owner"]]
        search = " OR ".join(searchrepos)
        logger.debug("Search string: '{}'", search)
        if search.strip() == "" or search == None:
            raise ValueError("Blank search result, no point searching...")
        search_result = list(github.github.search_repositories(query=search))

        # filter search results by owner
        if "owner" in kwargs_object:
            logger.debug("Filtering based on owner: {}", kwargs_object["owner"])
            filtered_result = [
                repo
                for repo in search_result
                if repo.owner.login in kwargs_object["owner"]
            ]
            search_result = list(filtered_result)
        # if you're not specifying it on the command line, filter the list by the config
        elif config["linter"]["owner_list"]:
            filtered_result = [
                repo
                for repo in search_result
                if repo.owner.login in config["linter"]["owner_list"]
            ]
            logger.warning("Filtering by owner list in linter config")
            search_result = list(filtered_result)
        # filter search results by repo name
        if "repo" in kwargs_object:
            # logger.debug("Filtering based on repo: {}", kwargs_object["repo"])
            filtered_result = [
                repo for repo in search_result if repo.name in kwargs_object["repo"]
            ]
            search_result = filtered_result

    else:
        search_result = get_all_user_repos(github)

    if not config["linter"]["check_forks"]:
        logger.debug("Filtering out forks")
        filtered_by_forks = [repo for repo in search_result if repo.fork is False]
        search_result = list(filtered_by_forks)

    logger.debug("Search result: {}", search_result)
    return search_result
