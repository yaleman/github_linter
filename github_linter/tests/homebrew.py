""" checks for homebrew things """

from hashlib import sha256

# from pathlib import Path
import sys

from loguru import logger

from .. import RepoLinter
from ..utils import get_fix_file_path
CATEGORY = "homebrew"

LANGUAGES = ["Ruby"]

def should_this_run(func):
    """ if the repo name doesn't match then don't run """
    def inner(repo: RepoLinter):
        if not repo.repository.name.startswith("homebrew-"):
            logger.debug("Not a homebrew repo, skipping")
            return None
        logger.debug("Name checks out: {}", repo.repository.name)
        return func(repo)
    return inner

REQUIRED_FILES = {
    "homebrew_check_latest_release.sh",
    ".github/workflows/homebrew_check_updates.yml",
}

@should_this_run
def check_update_files_exist(
    repo: RepoLinter
) -> None:
    """ checks that the required files exist """
    for filename in REQUIRED_FILES:
        filecontents = repo.cached_get_file(filename)
        if not filecontents:
            repo.error(CATEGORY, f"Missing homebrew file file: {filename}")


@should_this_run
def fix_update_files_exist(
    repo: RepoLinter
):
    """ copies the files up from the templates """

    for filename in REQUIRED_FILES:
        filecontents = repo.cached_get_file(filepath=filename, clear_cache=True)
        logger.debug("{} : {}", filename, filecontents )
        if filecontents:
            logger.debug("Filename already exists: {}", filename)
            continue

        # load the file
        updatefile = get_fix_file_path(CATEGORY, filename)
        if not updatefile.exists():
            logger.error("Running fix, can't find fix file {}!", updatefile.as_posix())
            sys.exit(1)

        filehash = sha256(updatefile.read_bytes()).hexdigest()

        result = repo.repository.update_file(
            path=filename,
            message=f"github_linter.homebrew.fix_update_file_exists({filename})",
            content = updatefile.read_bytes(),
            sha = filehash,
            branch = repo.repository.default_branch
            )
        commit = result["commit"]
        if not hasattr(commit, "commit"):
            continue
        # Log it
        repo.fix(
            CATEGORY,
            f"Updated {filename} in commit {getattr(commit,'html_url')}",
        )
