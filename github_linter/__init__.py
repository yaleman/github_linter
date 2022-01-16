""" goes through your repos and checks for things """

from collections import deque

from datetime import datetime
from json.decoder import JSONDecodeError
import os
from pathlib import Path
# import sys
import time
from types import ModuleType
from typing import Any, Dict, Optional, List, Tuple, Union

import json5 as json
from loguru import logger
from github import Github
from github.ContentFile import ContentFile
from github.GithubException import UnknownObjectException
from github.Repository import Repository
import pytz


from .types import DICTLIST

__version__ = "0.0.1"

def load_config() -> Dict[Optional[str],Any]:
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
    return {}

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

def get_filtered_commands(checklist: List[str], check_filter: Optional[Tuple]) -> List[str]:
    """ filters the checks """
    if not check_filter:
        return list(checklist)
    checks = []
    for check in checklist:
        for filterstr in check_filter:
            if check.startswith(filterstr) and check not in checks:
                checks.append(check)
                continue
    return checks

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
            fixes = []
            if "errors" in repo and repo["errors"]:
                for category in repo["errors"]:
                    deque(map(errors.append, [f"{category} - {error}" for error in repo["errors"].get(category)]))
            if "warnings" in repo and repo["warnings"]:
                for category in repo["warnings"]:
                    deque(map(warnings.append, [f"{category} - {warning}" for warning in repo["warnings"].get(category)]))
            if "fixes" in repo and repo["fixes"]:
                for category in repo["fixes"]:
                    deque(map(fixes.append, [f"{category} - {fix}" for fix in repo["fixes"].get(category)]))
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
        check: Optional[Tuple]
    ):
        """ Runs modules against the given repo """

        repolinter = RepoLinter(repo)
        self.current_repo = repolinter.repository

        logger.debug(repo.full_name)
        if repolinter.repository.archived:
            logger.warning("Repository {} is archived!", repolinter.repository.full_name)

        if repolinter.repository.parent:
            logger.warning("Parent: {}", repolinter.repository.parent.full_name)

        logger.debug("Enabled modules: {}", self.modules)
        for module in self.modules:
            repolinter.run_module(
                module=self.modules[module],
                check_filter=check,
                )

        if not repolinter.errors or repolinter.warnings:
            logger.debug("{} all good", repolinter.repository.full_name)
        self.report[repolinter.repository.full_name] = {
            "errors": repolinter.errors,
            "warnings": repolinter.warnings,
            "fixes" : repolinter.fixes,
        }

        time.sleep(self.check_rate_limits())

class RepoLinter:
    """ handles the repository object, its parent and the report details """
    def __init__(self, repo: Repository):
        """ startup things """
        self.config = load_config()
        if not self.config:
            self.config = {}

        self.repository = repo

        self.timings = {
            "start_time" : datetime.now(),
            "end_time" : None,
        }

        self.errors: DICTLIST = {}
        self.warnings: DICTLIST = {}
        self.fixes: DICTLIST = {}
        self.filecache: Dict[str,Optional[ContentFile]] = {}

    def clear_file_cache(self, filepath: str) -> bool:
        """ removes a file from the file cache, returns bool if it was in there """
        if filepath in self.filecache:
            del self.filecache[filepath]
            return True
        return False

    def cached_get_file(
        self,
        filepath: str,
        clear_cache: bool = False
        ) -> Optional[ContentFile]:
        """ checks if we've made a call looking for a file and grabs it if not
        returns none if no file exists, caches per-repository.
        """

        if clear_cache:
            self.clear_file_cache(filepath)
        elif filepath in self.filecache:
            return self.filecache[filepath]
        # cache and then return
        self.filecache[filepath] = self.get_file(filepath)
        return self.filecache[filepath]

    # def cached_get_files(
    #     self,
    #     path: str,
    #     ) -> Optional[ContentFile]:
    #     """ checks if we've made a call looking for files and grabs them if not
    #     returns none if no file exists, caches per-repository.
    #     """
    #     # cached call
    #     files = []

    #     for filename in path:
    #         if not pathendswith()
    #     if filepath in self.filecache:
    #         return self.filecache[filepath]
    #     # cache and then return
    #     self.filecache[filepath] = self.get_file(filepath)
    #     return self.filecache[filepath]

    def get_files(self, path: str) -> Optional[List[ContentFile]]:
        """ give it a path and it'll return the match(es). If it's a single file it'll get that, if it's a path it'll get up to 1000 files """
        try:
            fileresult = self.repository.get_contents(path)
            if not fileresult:
                logger.debug("Couldn't find files matching '{}'", path)
                return None
            if not isinstance(fileresult, list):
                fileresult = [fileresult,]
            return fileresult
        except UnknownObjectException as exc:
            logger.debug("UnknownObjectException calling get_contents({}): {}", path, exc)
            return None

    def get_file(
        self,
        filename: str
    ) -> Optional[ContentFile]:
        """ looks for a file or returns none"""
        try:
            fileresult = self.get_files(filename)
            if not fileresult:
                logger.debug("Couldn't find {}...?", filename)
                return None
            if isinstance(fileresult, list) and len(fileresult):
                return fileresult[0]
            return None
        except UnknownObjectException:
            logger.debug(
                "{} not found in {}",
                filename,
                self.repository.full_name,
            )
        return None

    def module_language_check(
        self,
        module : ModuleType,
    ) -> bool:
        """ checks a repo + module for the exposed languages and makes sure they line up

        returns True if any of the language modules is in the repo
        """

        if "all" in module.LANGUAGES:
            return True

        repo_langs = [ lang.lower() for lang in self.repository.get_languages() ]

        for language in module.LANGUAGES:
            if language.lower() in repo_langs:
                return True
        return False


    @classmethod
    def add_result(cls, result_object: DICTLIST, category: str, value: str) -> None:
        """ adds an result to the target object"""
        if category not in result_object:
            result_object[category] = []
        if value not in result_object[category]:
            result_object[category].append(value)
        logger.debug("{} - {}", category, value)

    def error(self, category: str, value: str):
        """ adds an error """
        self.add_result(self.errors, category, value)

    def fix(self, category: str, value: str):
        """ adds a fixed item """
        self.add_result(self.fixes, category, value)

    def warning(self, category: str, value: str):
        """ adds a warning """
        self.add_result(self.warnings, category, value)


    def run_module(
        self,
        module: ModuleType,
        check_filter: Optional[Tuple],
    ) -> bool:
        """ runs a given module """

        if "LANGUAGES" in dir(module):
            if not self.module_language_check(module):
                logger.debug(
                    "Module {} not required after language check, module langs: {}, repo langs: {}",
                    module.__name__.split(".")[-1],
                    module.LANGUAGES,
                    self.repository.get_languages(),
                    )
                return False

        for check in sorted(get_filtered_commands(dir(module), check_filter)):
            if check.startswith("check_"):
                logger.debug("Running {}.{}", module.__name__.split(".")[-1], check)
                getattr(module, check)(
                    repo=self,
                )
            if check.startswith("fix_"):
                logger.debug("Running {}.{}", module.__name__.split(".")[-1], check)
                getattr(module, check)(
                    repo=self
                )
            # else:
                # logger.debug("Skipping check: {}", check)

        return True
