"""repolinter class"""

from datetime import datetime
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Dict, List, Optional, Tuple, Union

import difflib
from github.ContentFile import ContentFile
from github.GithubException import GithubException, UnknownObjectException
from github.Repository import Repository
from github3.repos import ShortRepository
from loguru import logger
import tomli

import wildcard_matcher

from .exceptions import (
    NoChangeNeeded,
    SkipNoLanguage,
    SkipOnArchived,
    SkipOnPrivate,
    SkipOnProtected,
    SkipOnPublic,
)

from .custom_types import DICTLIST
from .utils import load_config


def add_from_dict(source: Dict[str, Any], dest: Dict[str, Any]) -> None:
    """digs into a dict, shoving the defaults in"""
    if not source:
        return
    logger.debug("Processing {}, {}", source, type(source))
    for key in source:
        logger.debug("Adding key={} {}", key, type(key))
        logger.debug("{}, {}", dest, type(dest))

        if hasattr(dest, str(key)):
            dest[key] = source[key]
        elif isinstance(dest, dict):
            logger.debug("Checking for {} in {}", key, dest)
            if key not in dest:
                dest[key] = source[key]
                continue

        # TODO: work out how to do this with a pydantic BaseModel
        if isinstance(dest[key], dict):
            add_from_dict(source[key], dest[key])


def get_filtered_commands(checklist: List[str], check_filter: Optional[Tuple[str]]) -> List[str]:
    """filters the checks, the input is the list of wanted modules
    from click.option()
    """
    if not check_filter:
        return list(checklist)
    checks = []
    for check in checklist:
        for filterstr in check_filter:
            if (filterstr in check or wildcard_matcher.match(check, filterstr)) and check not in checks:
                checks.append(check)
                continue
    return checks


class RepoLinter:
    """handles the repository object, its parent and the report details"""

    def __init__(
        self,
        repo: Repository,
        repo3: ShortRepository,
        ignore_protected: bool = False,
    ) -> None:
        """startup things"""
        self.config = load_config()
        self.ignore_protected = ignore_protected
        if not self.config:
            self.config = {}

        self.repository = repo
        self.repository3 = repo3

        self.timings = {
            "start_time": datetime.now(),
            "end_time": None,
        }

        self.errors: DICTLIST = {}
        self.warnings: DICTLIST = {}
        self.fixes: DICTLIST = {}
        self.filecache: Dict[str, Optional[ContentFile]] = {}

        self.languages: Optional[List[str]] = None

    def clear_file_cache(self, filepath: str) -> bool:
        """removes a file from the file cache, returns bool if it was in there"""
        if filepath in self.filecache:
            del self.filecache[filepath]
            return True
        return False

    def cached_get_file(self, filepath: str, clear_cache: bool = False) -> Optional[ContentFile]:
        """checks if we've made a call looking for a file and grabs it if not
        returns none if no file exists, caches per-repository.
        """

        if clear_cache:
            self.clear_file_cache(filepath)
        elif filepath in self.filecache:
            return self.filecache[filepath]
        # cache and then return

        try:
            self.filecache[filepath] = self.get_file(filepath)
        except GithubException as error_message:
            if "documentation_url" in error_message.data and isinstance(error_message.data, dict):
                docs_url = error_message.data["documentation_url"]
            else:
                docs_url = "Unknown docs URL"

            if isinstance(error_message.data, dict):
                message = str(error_message.data["message"])
            else:
                message = str(error_message.data)

            logger.error(
                "Failed to pull file '{}' : {} ({})",
                filepath,
                message,
                docs_url,
            )
            return None
        return self.filecache[filepath]

    # pylint: disable=too-many-branches
    def create_or_update_file(
        self,
        filepath: str,
        newfile: Union[Path, str, bytes],
        oldfile: Optional[ContentFile] = None,
        message: Optional[str] = None,
    ) -> Optional[str]:
        """Create or update a file in the repository.
        The message variable is what's put into the commit message.
        Returns the commit URL.
        """

        if not not self.ignore_protected:
            if self.repository3.branch(self.repository3.default_branch).protected:
                logger.warning(
                    "Can't update file on  {} as the default branch is protected",
                    self.repository3.full_name,
                )
                raise SkipOnProtected("Can't make changes to a protected branch")

        if not message:
            message = f"github-linter updating file: {filepath}"

        if isinstance(newfile, bytes):
            newfile_contents = newfile
        elif isinstance(newfile, str):
            newfile_contents = newfile.encode("utf-8")
        else:
            newfile_contents = newfile.read_bytes()

        if oldfile:
            if oldfile.decoded_content == newfile_contents:
                logger.debug("File content is up to date for {}", filepath)
                # TODO: probably should raise NoChangeNeeded when create_or_update_file finds there's no change required
                return None
            blobsha = oldfile.sha
        else:
            blobsha = ""

        commit_branch = self.config.get("fix_branch")
        if commit_branch is not None:
            # raise ValueError("Somehow we got a null value from the config for fix_branch while trying to commit a file!")
            if commit_branch != self.repository.default_branch:
                try:
                    target_branch = self.repository.get_branch(commit_branch)
                except GithubException as error:
                    if error.status != 404:
                        print(error)
                        sys.exit(1)
                    logger.debug(f"404'd looking for branch {commit_branch}, will commit one.")
                    source_branch = self.repository.get_branch(self.repository.default_branch)
                    branch_create = self.repository.create_git_ref(ref="refs/heads/" + commit_branch, sha=source_branch.commit.sha)
                    logger.debug(f"result of creating {commit_branch} from {self.repository.default_branch}: {branch_create}")
                    logger.info(
                        "Created branch {} in {}",
                        commit_branch,
                        self.repository.full_name,
                    )
            target_branch = self.repository.get_branch(commit_branch)
        else:
            target_branch = self.repository.get_branch(self.repository.default_branch)

        commit_result = self.repository.update_file(
            path=filepath,
            message=message,
            content=newfile_contents,
            sha=blobsha,
            branch=target_branch.name,
        )
        if "commit" not in commit_result:
            return "Unknown Commit URL"

        return getattr(commit_result["commit"], "html_url", "")

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

    def get_files(self, path: str) -> List[ContentFile]:
        """give it a path and it'll return the match(es). If it's a single file it'll get that, if it's a path it'll get up to 1000 files"""
        try:
            fileresult: List[ContentFile] | ContentFile = self.repository.get_contents(path)
            if not fileresult:
                logger.debug("Couldn't find files matching '{}'", path)
                return []
            if not isinstance(fileresult, list):
                return [
                    fileresult,
                ]
            return fileresult  # type: ignore [invalid-return-type]
        except GithubException as exc:
            if exc.status == 404:
                logger.debug("Couldn't find file, returning None - exception={}", exc)
                return []
            else:
                logger.error("GithubException calling get_contents({})", path)
                raise exc
        except UnknownObjectException as exc:
            logger.debug("UnknownObjectException calling get_contents({}): {}", path, exc)
            return []

    def get_file(self, filename: str) -> Optional[ContentFile]:
        """looks for a file or returns none"""
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
        module: ModuleType,
    ) -> bool:
        """checks a repo + module for the exposed languages and makes sure they line up

        returns True if any of the language modules is in the repo
        """

        if "all" in module.LANGUAGES:
            return True

        repo_langs = [lang.lower() for lang in self.repository.get_languages()]

        for language in module.LANGUAGES:
            if language.lower() in repo_langs:
                return True
        return False

    @classmethod
    def add_result(cls, result_object: DICTLIST, category: str, value: str) -> None:
        """adds an result to the target object"""
        if category not in result_object:
            result_object[category] = []
        if value not in result_object[category]:
            result_object[category].append(value)
        logger.debug("{} - {}", category, value)

    def error(self, category: str, value: str) -> None:
        """adds an error"""
        logger.error("{} - {}", category, value)
        self.add_result(self.errors, category, value)

    def fix(self, category: str, value: str) -> None:
        """adds a fixed item"""
        logger.success("{} - {}", category, value)
        self.add_result(self.fixes, category, value)

    def warning(self, category: str, value: str) -> None:
        """adds a warning"""
        logger.warning("{} - {}", category, value)
        self.add_result(self.warnings, category, value)

    def load_module_config(
        self,
        module: ModuleType,
    ) -> None:
        """mixes the config defaults in from the module with the config in the repository"""
        if not hasattr(module, "DEFAULT_CONFIG"):
            return
        module_name = module.__name__.split(".")[-1]
        logger.debug("Adding module-default config for {}", module_name)
        if module_name not in self.config:
            self.config[module_name] = {}

        module_config = self.config[module_name]
        if isinstance(module.DEFAULT_CONFIG, dict):
            add_from_dict(module.DEFAULT_CONFIG, module_config)
        elif hasattr(module.DEFAULT_CONFIG, "model_validate"):
            # we're dealing with a pydantic model
            add_from_dict(module.DEFAULT_CONFIG.model_dump(), module_config)
        else:
            raise ValueError(f"The default config for {module_name} isn't a dict or pydantic BaseModel!")

    def skip_on_archived(self) -> None:
        """Add this to a check to skip it if the repository is archived."""
        if self.repository.archived:
            raise SkipOnArchived("This repository is archived so this test doesn't need to run.")

    def skip_on_protected(self) -> None:
        """Add this to a check to skip it if the repository has a protected main branch."""
        if self.repository.archived:
            raise SkipOnProtected("This repository has a protected main branch so we can't run here.")

    def skip_on_private(self) -> None:
        """Add this to a check to skip it if the repository is private."""
        if self.repository.private:
            raise SkipOnPrivate("This repository is private so this test can't run.")

    def skip_on_public(self) -> None:
        """Add this to a check to skip it if the repository is public."""
        if not self.repository.private:
            raise SkipOnPublic("This repository is public so this test can't run.")

    def run_module(
        self,
        module: ModuleType,
        check_filter: Optional[Tuple[str]],
        do_fixes: bool,
    ) -> bool:
        """runs a given module"""
        self.load_module_config(module)

        if hasattr(module, "LANGUAGES") and "ALL" not in getattr(module, "LANGUAGES"):
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
                try:
                    getattr(module, check)(
                        repo=self,
                    )
                except (
                    SkipOnArchived,
                    SkipOnPrivate,
                    SkipOnPublic,
                    SkipNoLanguage,
                    NoChangeNeeded,
                ):
                    pass
            if do_fixes:
                if check.startswith("fix_"):
                    logger.debug("Running {}.{}", module.__name__.split(".")[-1], check)
                    try:
                        getattr(module, check)(repo=self)
                    except (
                        NoChangeNeeded,
                        SkipOnArchived,
                        SkipOnPrivate,
                        SkipOnPublic,
                        NoChangeNeeded,
                        SkipOnProtected,
                    ):
                        pass
        return True

    def requires_language(self, language: str) -> None:
        """raises a skip exception if the repository doesn't have this language"""
        if self.languages is None:
            self.languages = [str(key) for key in self.repository.get_languages().keys()]
        logger.debug("Languages in repo: {}", ",".join(self.languages))
        if language not in self.languages:
            logger.debug("Didn't find {} in language list, raising SkipNoLanguage")
            raise SkipNoLanguage
        logger.debug("Found {} in repo's language list", language)

    def load_pyproject(self) -> Optional[Dict[str, Any]]:
        """loads the pyproject.toml file"""

        fileresult = self.cached_get_file("pyproject.toml")
        if not fileresult:
            logger.debug("No content for pyproject.toml")
            return None

        try:
            retval: Dict[str, Any] = tomli.loads(fileresult.decoded_content.decode("utf-8"))
            return retval
        except tomli.TOMLDecodeError as tomli_error:
            logger.debug(
                "Failed to parse {}/pyproject.toml: {}",
                self.repository.full_name,
                tomli_error,
            )
            return None

    def diff_file(self, old_file: str, new_file: str) -> None:
        """diffs two files using difflib"""
        diff = difflib.unified_diff(old_file.splitlines(), new_file.splitlines(), fromfile="old", tofile="new")
        for line in diff:
            logger.warning(line)
