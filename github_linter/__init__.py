""" goes through your repos and checks for things """

from datetime import datetime
from json.decoder import JSONDecodeError
import os
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Dict, Optional, List

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

# pylint: disable=too-few-public-methods
class GithubLinter:
    """ does things """

    def __init__(self):
        """ setup """
        if os.getenv("GITHUB_TOKEN"):
            logger.debug("Using GITHUB_TOKEN")
            self.github = Github(os.getenv("GITHUB_TOKEN"))

        self.config = load_config()
        if not self.config:
            self.config = {}

        self.current_repo: Optional[Repository] = None
        self.report = {}
        self.modules: Dict[str, ModuleType] = {}
        self.filecache: Dict[str, Dict[str,Optional[ContentFile]]] = {}

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
                    if repo["errors"][category]:
                        errors = [f" - {error}" for error in repo["errors"][category]]
            if "warnings" in repo and repo["warnings"]:
                for category in repo["warnings"]:
                    if repo["warnings"][category]:
                        warnings = [
                            f" - {warning}" for warning in repo["warnings"][category]
                        ]
            if errors or warnings:
                logger.info("Report for {}", repo_name)
                for error in errors:
                    logger.error(error)
                for warning in warnings:
                    logger.warning(warning)
            else:
                logger.info("Repository {} checks out OK", repo_name)

    def handle_repo(
        self,
        repo: Repository,
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
            self.run_module(errors, warnings, self.modules[module])

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
        filepath: str
        ) -> Optional[ContentFile]:
        """ checks if we've made a call looking for a file and grabs it if not
        returns none if no file exists
        """
        if not self.current_repo:
            raise RepositoryNotSet
        if self.current_repo.full_name not in self.filecache:
            self.filecache[self.current_repo.full_name] = {}
        repo_cache = self.filecache[self.current_repo.full_name]

        # cached call
        if filepath in repo_cache:
            return repo_cache[filepath]
        # cache and then return
        repo_cache[filepath] = get_file_from_repo(self.current_repo, filepath)
        return repo_cache[filepath]

    def run_module(
        self,
        errors_object: DICTLIST,
        warnings_object: DICTLIST,
        module: ModuleType,
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

        for check in dir(module):
            if check.startswith("check_"):
                logger.debug("Running {}", check)
                getattr(module, check)(
                    self, errors_object, warnings_object
                )
        return True
