""" goes through your repos and checks for things """

from collections import deque

from datetime import datetime
import itertools

import os
import time
from types import ModuleType
from typing import Any, Dict, Optional, List, Tuple

import json5 as json
from loguru import logger
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
import github3  # type: ignore
from github3.repos.repo import ShortRepository  # type: ignore
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
    """does things"""

    def __init__(self) -> None:
        """setup"""
        self.config = load_config()
        if not self.config:
            self.config = {}

        self.github = self.do_login()
        self.github3 = self.do_login3()

        self.current_repo: Optional[Repository] = None
        self.report: Dict[str, Any] = {}
        self.modules: Dict[str, ModuleType] = {}
        self.filecache: Dict[str, Dict[str, Optional[ContentFile]]] = {}

        self.do_login3()

    def do_login3(self) -> github3.GitHub:
        """Does the login phase for github3.py"""

        if os.getenv("GITHUB_TOKEN"):
            logger.debug("Using GITHUB_TOKEN environment variable for login.")
            self.github3 = github3.login(token=os.getenv("GITHUB_TOKEN"))
            logger.debug("Checking github3 login: {}", self.github3.me())
            return self.github3
        if (
            "ignore_auth" in self.config["github"]
            and self.config["github"]["ignore_auth"]
        ):
            self.github = Github()
            return self.github
        if "token" in self.config["github"]:
            self.github3 = github3.login(token=self.config["github"]["token"])
            return self.github3

        logger.error("Can't login using the github3 library without a token.")
        raise ValueError("No authentication method was found!")

    def do_login(self) -> Github:
        """does the login/auth bit"""

        if os.getenv("GITHUB_TOKEN"):
            logger.debug("Using GITHUB_TOKEN environment variable for login.")
            self.github = Github(os.getenv("GITHUB_TOKEN"))
            return self.github
        if "github" in self.config and self.config["github"]:
            if (
                "ignore_auth" in self.config["github"]
                and self.config["github"]["ignore_auth"]
            ):
                self.github = Github()
                return self.github
            if "token" in self.config["github"]:
                self.github = Github(login_or_token=self.config["github"]["token"])
                return self.github
            if (
                "username" in self.config["github"]
                and "password" in self.config["github"]
            ):
                self.github = Github(
                    login_or_token=self.config["github"]["username"],
                    password=self.config["github"]["password"],
                )
                return self.github
        raise ValueError("No authentication method was found!")

    @pydantic.validate_call(config={"arbitrary_types_allowed": True})
    def add_module(self, module_name: str, module: ModuleType) -> None:
        """adds a module to modules"""
        self.modules[module_name] = module

    def check_rate_limits(self) -> int:
        """checks the rate limits and returns a number of seconds to wait"""
        rate_limits = self.github.get_rate_limit()
        logger.debug(json.dumps(rate_limits, indent=4, default=str, ensure_ascii=False))
        sleep_time = 0

        for rate_type in RATELIMIT_TYPES:
            if hasattr(rate_limits, rate_type):
                remaining = getattr(rate_limits, rate_type).remaining
                reset = getattr(rate_limits, rate_type).reset.astimezone(pytz.utc)
                logger.debug("Rate limit remaining: {}", remaining)
                logger.debug("Rate limit reset time: {}", reset)

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

    def display_report(self) -> None:
        """displays a report"""
        for repo_name in self.report:
            repo = self.report[repo_name]
            if not repo:
                logger.warning("Empty report for {}, skipping", repo_name)
            errors: List[str] = []
            warnings: List[str] = []
            fixes: List[str] = []
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
                deque(map(logger.success, fixes))
            else:
                logger.info("Repository {} checks out OK", repo_name)

    # @pydantic.validate_arguments(config={"arbitrary_types_allowed": True})
    def handle_repo(
        self,
        repo: ShortRepository,
        check: Optional[Tuple[str]],
        fix: bool,
    ) -> None:
        """Runs modules against the given repo"""

        github_repo = self.github.get_repo(repo.full_name)

        repolinter = RepoLinter(github_repo, repo)

        self.current_repo = repolinter.repository

        logger.info("Current repo: {}", repo.full_name)
        if repolinter.repository.archived:
            logger.warning(
                "Repository {} is archived!", repolinter.repository3.full_name
            )

        if repolinter.repository.parent:
            logger.warning("Parent: {}", repolinter.repository.parent.full_name)

        logger.debug("Enabled modules: {}", self.modules)

        if repo.archived and fix:
            logger.warning("Not doing fixes on archived repository {}", repo.full_name)

            for module in self.modules:
                repolinter.run_module(
                    module=self.modules[module],
                    check_filter=check,
                    do_fixes=False,
                )
        else:
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


@pydantic.validate_call(config={"arbitrary_types_allowed": True})
def get_all_user_repos(
    github: GithubLinter, config: Optional[Dict[str, Any]] = None
) -> List[str]:
    """simpler filtered listing"""
    if config is None:
        config = load_config()

    if config["linter"].get("owner_list", []):
        repolist = []

        for owner in config["linter"]["owner_list"]:
            logger.debug("Pulling all the repositories for {}", owner)
            if config.get("linter", {}).get("repo_filter") is not None:
                for repo in github.github3.repositories_by(
                    username=owner, type="owner"
                ):
                    if repo.name in config["linter"]["repo_filter"]:
                        repolist.append(repo.full_name)
            else:
                repolist.extend(
                    [repo.full_name for repo in github.github3.repositories(owner)]
                )
    else:
        logger.debug("Pulling all the repositories I own")
        repolist = [
            repo.full_name for repo in github.github3.repositories(type="owner")
        ]
    logger.debug("Repo list: {}", ", ".join(repolist))
    return repolist


@pydantic.validate_call(config={"arbitrary_types_allowed": True})
def filter_by_repo(
    repo_list: List[Repository], repo_filters: List[str]
) -> List[Repository]:
    """filter repositories by name"""
    retval = []
    for repository in repo_list:
        if repository.name in repo_filters:
            if repository not in retval:
                retval.append(repository)
                logger.debug("Adding {} based on name match", repository)
            continue
        for repo_filter in repo_filters:
            if "*" in repo_filter:
                if wildcard_matcher.match(repository.name, repo_filter):
                    if repository not in retval:
                        retval.append(repository)
                    logger.debug("Adding {} based on wildcard match", repository)
                    continue

    return retval


class RepoSearchString(pydantic.BaseModel):  # pylint: disable=no-member
    """Result of running generate_repo_search_string"""

    needs_post_filtering: bool
    search_string: str


@pydantic.validate_call
def generate_repo_search_string(
    repo_filter: List[str],
    owner_filter: List[str],
) -> RepoSearchString:
    """generates the search string,
    if there's wildcards in repo_filter, then you
    have to search for *everything* then filter it later
    """

    has_repo_wildcard = False
    for filterstring in repo_filter:
        if "*" in filterstring:
            has_repo_wildcard = True
            logger.debug(
                "Falling back to owner-only search because of a wildcard in the repo_filter ({})",
                filterstring,
            )
            break

    if has_repo_wildcard or not repo_filter:
        search_string = ""
        logger.debug("Adding owner filter")
        search_string += " ".join([f"user:{owner.strip()}" for owner in owner_filter])
        logger.debug("Search string: {}", search_string)
        return RepoSearchString(
            needs_post_filtering=has_repo_wildcard, search_string=search_string
        )

    search_chunks = []
    for owner, repo in itertools.product(owner_filter, repo_filter):
        combo = f"repo:{owner.strip()}/{repo.strip()}"
        # logger.debug(combo)
        search_chunks.append(combo)
    search_string = " ".join(search_chunks)
    logger.debug("Search string: {}", search_string)
    return RepoSearchString(needs_post_filtering=False, search_string=search_string)


@pydantic.validate_call(config={"arbitrary_types_allowed": True})
def search_repos(
    github: GithubLinter,
    repo_filter: List[str],
    owner_filter: List[str],
) -> List[github3.repos.repo.ShortRepository]:
    """search repos based on cli input"""

    username = github.github3.me().login
    logger.debug("Logged in as username {}", username)

    if not owner_filter:
        logger.debug("Pulling owner filter from config")
        if (
            "owner_list" in github.config["linter"]
            and len(github.config["linter"]["owner_list"]) != 0
        ):
            owner_filter = github.config["linter"]["owner_list"]
        else:
            logger.info("No owner filter, using username")
            owner_filter = [username]
    else:
        logger.debug("Using owner filter: {}", owner_filter)

    logger.debug("Username: {}", username)
    logger.debug("Repo Filter: {}", repo_filter)

    results = []

    # we're specifically looking for some
    if len(repo_filter) > 0:
        for repo_name in repo_filter:
            for owner in owner_filter:
                try:
                    repo_get = github.github3.repository(
                        owner=owner, repository=repo_name
                    )
                    if repo_get is not None:
                        logger.debug("Adding {}", repo_get.name)
                        results.append(repo_get)
                except github3.exceptions.NotFoundError:
                    pass
    else:
        # pull the private ones because that's a thing
        if username in owner_filter:
            repos = github.github3.repositories(type="private")
            logger.debug("Found repos: {}", repos)
            for repo in repos:
                if len(repo_filter) > 0:
                    if repo.name in repo_filter:
                        results.append(repo)
                    else:
                        logger.debug("Skipping {} != {}", repo.name, repo_filter)
                elif repo not in results:
                    logger.debug("Adding {}", repo)
                    results.append(repo)

        # pull everything else
        for owner in owner_filter:
            logger.debug("Pulling repos for {}", owner)
            repos = github.github3.repositories_by(username=owner, type="owner")
            logger.debug("Found repos: {}", repos)
            for repo in repos:
                if len(repo_filter) > 0:
                    if repo.name in repo_filter:
                        results.append(repo)
                    else:
                        logger.debug("Skipping {} != {}", repo.name, repo_filter)
                elif repo not in results:
                    logger.debug("Adding {}", repo)
                    results.append(repo)
    # filter by repo.owner.login

    results = [repo for repo in set(results) if repo.owner.login in owner_filter]

    logger.debug("Found repos: {}", ", ".join([str(result) for result in results]))
    logger.debug("Found {} repos", len(results))
    return results
