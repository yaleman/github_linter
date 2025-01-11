"""checks for homebrew things"""

import sys
from typing import List, TypedDict, Callable, TypeVar, cast
from loguru import logger  # type: ignore

from ..repolinter import RepoLinter
from ..utils import get_fix_file_path

CATEGORY = "homebrew"

LANGUAGES = ["Ruby"]


class DefaultConfig(TypedDict):
    """config typing for module config"""

    required_files: List[str]


DEFAULT_CONFIG: DefaultConfig = {
    "required_files": [
        "homebrew_check_latest_release.sh",
        ".github/workflows/homebrew_check_updates.yml",
    ]
}


WrappedFunction = TypeVar("WrappedFunction", bound=Callable[[RepoLinter], None])


def should_this_run(func: WrappedFunction) -> WrappedFunction:
    """if the repo name doesn't match then don't run"""

    def inner(repo: RepoLinter) -> None:
        if not repo.repository.name.startswith("homebrew-"):
            logger.debug("Not a homebrew repo, skipping")
            return None
        logger.debug("Name checks out: {}", repo.repository.name)
        func(repo)
        return None

    return cast(WrappedFunction, inner)


@should_this_run
def check_update_files_exist(repo: RepoLinter) -> None:
    """checks that the required files exist"""
    for filename in repo.config[CATEGORY]["required_files"]:
        filecontents = repo.cached_get_file(filename)
        if not filecontents:
            repo.error(CATEGORY, f"Missing homebrew file file: {filename}")


@should_this_run
def fix_update_files_exist(repo: RepoLinter) -> None:
    """updates the homebrew files from the templates"""

    for filename in repo.config[CATEGORY]["required_files"]:
        updatefile = get_fix_file_path(CATEGORY, filename)
        if not updatefile.exists():
            logger.error("Running fix, can't find fix file {}!", updatefile.as_posix())
            sys.exit(1)

        filecontents = repo.cached_get_file(filepath=filename, clear_cache=True)

        result = repo.create_or_update_file(
            filename,
            updatefile,
            filecontents,
            f"github_linter.homebrew updating {filename}",
        )
        if result is not None:
            repo.fix(
                CATEGORY,
                f"Updated {filename} in commit {result}",
            )
