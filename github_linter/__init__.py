""" goes through your repos and checks for things """

from collections import deque

from datetime import datetime
import itertools

import os
from re import search
import time
from types import ModuleType
from typing import Dict, Optional, List, Tuple

import json5 as json
from loguru import logger
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
import pydantic
import pytz
import wildcard_matcher

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

    @pydantic.validate_arguments(config=dict(arbitrary_types_allowed=True))
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


    @pydantic.validate_arguments(config=dict(arbitrary_types_allowed=True))
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


@pydantic.validate_arguments(config=dict(arbitrary_types_allowed=True))
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


@pydantic.validate_arguments(config=dict(arbitrary_types_allowed=True))
def filter_by_repo(
    repo_list: List[Repository],
    repo_filters: List[str]
) -> List[Repository]:
    """ filter repositories by name """
    retval = []
    for repository in repo_list:
        if repository.name in repo_filters:
            if repository not in retval:
                retval.append(repository)
                logger.debug("Adding {} based on name match", repository.name)
            continue
        for repo_filter in repo_filters:
            if "*" in repo_filter:
                if wildcard_matcher.match(repository.name, repo_filter):
                    if repository not in retval:
                        retval.append(repository)
                    logger.debug("Adding {} based on wildcard match", repository.name)
                    continue
    return retval


class RepoSearchString(pydantic.BaseModel): #pylint: disable=no-member
    """ Result of running generate_repo_search_string"""
    needs_post_filtering: bool
    search_string: str

@pydantic.validate_arguments
def generate_repo_search_string(
    repo_filter: List[str],
    owner_filter: List[str],
    ) -> RepoSearchString:
    """ generates the search string,
        if there's wildcards in repo_filter, then you
        have to search for *everything* then filter it later
    """

    has_repo_wildcard = False
    for filterstring in repo_filter:
        if "*" in filterstring:
            has_repo_wildcard = True
            logger.debug("Falling back to owner-only search because of a wildcard in the repo_filter ({})", filterstring)
            break

    if has_repo_wildcard or not repo_filter:
        search_string = ""
        logger.debug("Adding owner filter")
        search_string += " ".join([f"user:{owner.strip()}" for owner in owner_filter])
        logger.debug("Search string: {}", search_string)
        return RepoSearchString(needs_post_filtering=has_repo_wildcard, search_string=search_string)

    search_chunks = []
    for owner, repo in itertools.product(owner_filter, repo_filter):
        combo = f"repo:{owner.strip()}/{repo.strip()}"
        # logger.debug(combo)
        search_chunks.append(combo)
    search_string = " ".join(search_chunks)
    logger.debug("Search string: {}", search_string)
    return RepoSearchString(needs_post_filtering=False, search_string=search_string)

@pydantic.validate_arguments(config=dict(arbitrary_types_allowed=True))
def search_repos(
    github: GithubLinter,
    repo_filter: List[str],
    owner_filter: List[str],
) -> List[Repository]:
    """ search repos based on cli input """

    config = load_config()

    if not owner_filter:
        if "owner_list" in github.config["linter"] and len(github.config["linter"]["owner_list"]) != 0:
            owner_filter = github.config["linter"]["owner_list"]
        else:
            owner_filter = [github.github.get_user().login]


    # if it's just the user, then we can query easier
    if set(owner_filter) == set(github.github.get_user().login) and not repo_filter:
        repos = list(get_all_user_repos(github))

    else:
        search_string = generate_repo_search_string(repo_filter, owner_filter)
        repos = list(github.github.search_repositories(search_string.search_string))

        if search_string.needs_post_filtering:
            repos = filter_by_repo(repos, repo_filter)


    if not config["linter"].get("check_forks", None):
        logger.debug("Filtering out forks")
        filtered_by_forks = [repo for repo in repos if repo.fork is False]
        repos = filtered_by_forks

    logger.debug("Search result: {}", repos)
    return repos
