""" goes through your repos and checks for things """

from collections import deque

from datetime import datetime
from json.decoder import JSONDecodeError
import os
from pathlib import Path
# import sys
import time
from types import ModuleType
from typing import Dict, Optional, List, Tuple, Union

import json5 as json
from loguru import logger
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
import pytz
from github_linter.exceptions import RepositoryNotSet

from .types import DICTLIST
from .utils import add_result, get_file_from_repo
__version__ = "0.0.1"

def load_config() -> Optional[Dict[str, str]]:
    """ loads config """
    for configfile in [
        Path("./github_linter.json"),
        Path(os.path.expanduser("~/.config/github_linter.json")),
    ]:
        if not configfile.exists():
            continue
        try:
            config = json.load(configfile.open(encoding="utf8"))
            logger.debug("Using config file {}", configfile.as_posix())
            return config
        except JSONDecodeError as json_error:
            logger.error("Failed to load {}: {}", configfile.as_posix(), json_error)
    logger.error("Failed to find config file")
    return None

RATELIMIT_TYPES = {
    "core" : {
        "minlimit" : 50,
    },
    "graphql" : {
        "minlimit" : 5,
    },
    "search" : {
        "minlimit" : 1,
    },
}

def get_filtered_checks(checklist: List[str], check_filter: Optional[Tuple]) -> List[str]:
    """ filters the checks """

    if not check_filter:
        return list(checklist)
    checks = []
    for check in checklist:
        for filterstr in check_filter:
            if check.startswith(filterstr):
                checks.append(check)
                continue
    return checks

# pylint: disable=too-few-public-methods
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
        self.filecache: Dict[str, Dict[str,Optional[ContentFile]]] = {}

    def do_login(self) -> None:
        """ does the login/auth bit """

        if "github" not in self.config:
            if os.getenv("GITHUB_TOKEN"):
                logger.debug("Using GITHUB_TOKEN environment variable for login.")
                self.github = Github(os.getenv("GITHUB_TOKEN"))
        else:
            if "github" not in self.config:
                raise ValueError("No 'github' key in config, and no GITHUB_TOKEN auth - cannot start up.")
            if "ignore_auth" in self.config["github"] and self.config["github"]["ignore_auth"]:
                self.github = Github()
            elif "username" not in self.config["github"] or "password" not in self.config["github"]:
                raise ValueError("No authentication details available - cannot start up.")
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
            if "errors" in repo and repo["errors"]:
                for category in repo["errors"]:
                    deque(map(errors.append, [f"{category} - {error}" for error in repo["errors"].get(category)]))
            if "warnings" in repo and repo["warnings"]:
                for category in repo["warnings"]:
                    deque(map(warnings.append, [f"{category} - {warning}" for warning in repo["warnings"].get(category)]))
            if errors or warnings:
                logger.info("Report for {}", repo_name)
                # deque forces map to just run
                deque(map(logger.error, errors))
                deque(map(logger.warning, warnings))
            else:
                logger.info("Repository {} checks out OK", repo_name)

    def handle_repo(
        self,
        repo: Repository,
        check: Optional[Tuple]
    ):
        """ Runs modules against the given repo """

        self.current_repo = repo

        logger.debug(repo.full_name)
        if repo.archived:
            logger.warning("Repository is archived!")

        errors: DICTLIST = {}
        warnings: DICTLIST = {}
        if repo.parent:
            logger.warning("Parent: {}", repo.parent.full_name)

        logger.debug("Enabled modules: {}", self.modules)
        for module in self.modules:
            self.run_module(errors, warnings, self.modules[module], check)

        if not errors or warnings:
            logger.debug("{} all good", repo.full_name)
        self.report[repo.full_name] = {
            "errors": errors,
            "warnings": warnings,
        }

        time.sleep(self.check_rate_limits())

    def module_language_check(
        self,
        module : ModuleType,
    ) -> bool:
        """ checks a repo + module for the exposed languages and makes sure they line up

        returns True if any of the language modules is in the repo
        """

        if not self.current_repo:
            raise RepositoryNotSet

        if "all" in module.LANGUAGES:
            return True

        repo_langs = [ lang.lower() for lang in self.current_repo.get_languages() ]

        for language in module.LANGUAGES:
            if language.lower() in repo_langs:
                return True
        return False

    def cached_get_file(
        self,
        filepath: str,
        repository: Optional[Repository] = None,
        ) -> Optional[ContentFile]:
        """ checks if we've made a call looking for a file and grabs it if not
        returns none if no file exists, caches per-repository.
        """
        repo = self.current_repo
        if repository:
            repo = repository
        if not repo:
            raise RepositoryNotSet

        if repo.full_name not in self.filecache:
            self.filecache[repo.full_name] = {}
        repo_cache = self.filecache[repo.full_name]

        # cached call
        if filepath in repo_cache:
            return repo_cache[filepath]
        # cache and then return
        repo_cache[filepath] = get_file_from_repo(repo, filepath)
        return repo_cache[filepath]

    def run_module(
        self,
        errors_object: DICTLIST,
        warnings_object: DICTLIST,
        module: ModuleType,
        check_filter: Optional[Tuple]
    ) -> bool:
        """ runs a given module """

        if not self.current_repo:
            raise RepositoryNotSet

        if "LANGUAGES" in dir(module):
            if not self.module_language_check(module):
                logger.debug(
                    "Module {} not required after language check, module langs: {}, repo langs: {}",
                    module.__name__.split(".")[-1],
                    module.LANGUAGES,
                    self.current_repo.get_languages(),
                    )
                return False


        for check in get_filtered_checks(dir(module), check_filter):
            if check.startswith("check_"):
                logger.debug("Running {}.{}", module.__name__.split(".")[-1], check)
                getattr(module, check)(
                    self, errors_object, warnings_object
                )
        return True
