""" goes through your repos and checks for things """

from datetime import datetime
from json.decoder import JSONDecodeError
import os
from pathlib import Path
import time
from types import ModuleType
from typing import Union, Dict

import json5 as json
from loguru import logger
from github import Github
from github.Repository import Repository
import pytz

from .types import DICTLIST

__version__ = "0.0.1"

def load_config() -> Union[Dict[str, str], bool]:
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
    return False

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

        self.report = {}
        self.modules: Dict[str, ModuleType] = {}

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
        time.sleep(self.check_rate_limits())

        logger.debug(repo.full_name)
        if repo.archived:
            logger.warning("Repository is archived!")

        errors: DICTLIST = {}
        warnings: DICTLIST = {}
        if repo.parent:
            logger.warning("Parent: {}", repo.parent.full_name)

        logger.debug("Enabled modules: {}", self.modules)
        for module in self.modules:
            self.run_module(repo, errors, warnings, self.modules[module])

        if not errors or warnings:
            logger.debug("{} all good", repo.full_name)
        self.report[repo.full_name] = {
            "errors": errors,
            "warnings": warnings,
        }

    def run_module(
        self,
        repo_object: Repository,
        errors_object: DICTLIST,
        warnings_object: DICTLIST,
        module: ModuleType,
    ) -> bool:
        """ runs a given module """

        for check in dir(module):
            if check.startswith("check_"):
                logger.debug("Running {}", check)
                getattr(module, check)(
                    self, repo_object, errors_object, warnings_object
                )
        return True
