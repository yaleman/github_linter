""" template test file """

from typing import TypedDict, Optional, Union, List, Dict
from loguru import logger
from ..repolinter import RepoLinter


class DefaultConfig(TypedDict):
    """ config object """

    codeowners: Optional[Dict[str, Union[List[str], str]]]


CATEGORY = ""
DEFAULT_CONFIG: DefaultConfig = {
    "codeowners": None,
}

LANGUAGES = [ "ALL" ]



def check_codeowners_exists(repo: RepoLinter) -> None:
    """checks that CODEOWNERS exists in the root of the repo
    after checking that you require it by setting it in the config"""

    if not repo.config[CATEGORY]["codeowners"]:
        logger.warning("Skipping check as codeowners aren't configured.")

    filecontents = repo.cached_get_file("CODEOWNERS")
    if not filecontents:
        repo.error(CATEGORY, "CODEOWNERS file doesn't exist.")


def fix_codeowners_exists(repo: RepoLinter) -> None:
    """ makes a basic CODEOWNERS file based on the input """

    filepath = "CODEOWNERS"

    oldfile = repo.cached_get_file(filepath)

    filecontents = """# This file was created by github-linter\n"""
    if not repo.config[CATEGORY]["codeowners"]:
        logger.warning("Skipping fix as codeowners aren't configured.")

    for codeowner_path in repo.config[CATEGORY]["codeowners"]:
        filecontents += f"{codeowner_path} "
        if repo.config[CATEGORY]["codeowners"][codeowner_path] is not None:
            owner = repo.config[CATEGORY]["codeowners"][codeowner_path]
            if isinstance(owner, str):
                filecontents += f"{owner}\n"
            else:
                filecontents += f" {','.join(owner)}\n"

    if oldfile is not None and oldfile.decoded_content.decode("utf-8") == filecontents:
        logger.debug("Don't need to update {}", filepath)
        return
    # TODO: prompt the user to continue
    commit_url = repo.create_or_update_file(
        filepath=filepath,
        newfile=filecontents,
        oldfile=oldfile,
        message="github-linter updated CODEOWNERS file.",
    )
    repo.fix(CATEGORY, f"Created basic CODEOWNERS file: {commit_url}")

