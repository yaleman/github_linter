""" checks for homebrew things """

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
    """ updates the homebrew files from the templates """

    for filename in REQUIRED_FILES:

        updatefile = get_fix_file_path(CATEGORY, filename)
        if not updatefile.exists():
            logger.error("Running fix, can't find fix file {}!", updatefile.as_posix())
            sys.exit(1)

        filecontents = repo.cached_get_file(filepath=filename, clear_cache=True)

        logger.debug("{} : {}", filename, filecontents )
        if filecontents:
            if filecontents.decoded_content == updatefile.read_bytes():
                logger.debug("File content is up to date for {}", filename)
                continue
            blobsha = filecontents.sha
        else:
            blobsha = ""

        result = repo.repository.update_file(
            path=filename,
            message=f"github_linter.homebrew.fix_update_file_exists({filename})",
            content = updatefile.read_bytes(),
            sha = blobsha,
            branch = repo.repository.default_branch
            )
        commit = result["commit"]
        # Log it
        repo.fix(
            CATEGORY,
            f"Updated {filename} in commit {getattr(commit,'html_url', '')}",
        )
