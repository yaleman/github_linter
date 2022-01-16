""" checks for homebrew things """

from loguru import logger

from .. import RepoLinter

CATEGORY = "homebrew"

LANGUAGES = ["Ruby"]

def check_update_files_exist(
    repo: RepoLinter
) -> None:
    """ checks that the required files exist """
    if not repo.repository.name.startswith("homebrew-"):
        logger.debug("Not a homebrew repo, skipping")
    for filename in [
        "homebrew_check_latest_release.sh",
        ".github/workflows/homebrew_check_updates.yml",
    ]:
        filecontents = repo.cached_get_file(filename)
        if not filecontents:
            repo.error(CATEGORY, f"Missing homebrew file file: {filename}")
