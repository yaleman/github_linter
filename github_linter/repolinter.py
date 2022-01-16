""" repolinter class """

from datetime import datetime
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple

from github.ContentFile import ContentFile
from github.GithubException import UnknownObjectException
from github.Repository import Repository
# import json5 as json
from loguru import logger
import wildcard_matcher

from .types import DICTLIST
from .utils import load_config

def add_from_dict(source: Dict[str, Any], dest: Dict[str, Any]):
    """ digs into a dict, shoving the defaults in """
    for key in source:
        if key not in dest:
            dest[key] = source[key]
            continue

        if isinstance(dest[key], dict):
            add_from_dict(source[key], dest[key])

def get_filtered_commands(checklist: List[str], check_filter: Optional[Tuple]) -> List[str]:
    """ filters the checks """
    if not check_filter:
        return list(checklist)
    checks = []
    for check in checklist:
        for filterstr in check_filter:
            if (check.startswith(filterstr) or wildcard_matcher.match(check, filterstr)) \
                and check not in checks:
                checks.append(check)
                continue
    return checks

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

    def load_module_config(
        self,
        module: ModuleType,
    ):
        """ mixes the config defaults in from the module with the config in the repository """
        if not hasattr(module, "DEFAULT_CONFIG"):
            return
        module_name = module.__name__.split(".")[-1]
        logger.error("Adding module-default config for {}", module_name)
        if module_name not in self.config:
            self.config[module_name] = {}

        module_config = self.config[module_name]
        # logger.debug(json.dumps(self.config, indent=4, default=str, ensure_ascii=False))
        add_from_dict(module.DEFAULT_CONFIG, module_config)
        # logger.debug(json.dumps(self.config, indent=4, default=str, ensure_ascii=False))

    def run_module(
        self,
        module: ModuleType,
        check_filter: Optional[Tuple],
        do_fixes: bool,
    ) -> bool:
        """ runs a given module """
        self.load_module_config(module)


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
            if do_fixes:
                if check.startswith("fix_"):
                    logger.debug("Running {}.{}", module.__name__.split(".")[-1], check)
                    getattr(module, check)(
                        repo=self
                    )
            # else:
                # logger.debug("Skipping check: {}", check)

        return True
