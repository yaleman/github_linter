""" security.md test file """

from typing import TypedDict

from loguru import logger

from ..repolinter import RepoLinter
from ..utils import generate_jinja2_template_file

class DefaultConfig(TypedDict):
    """ default config for the test module """
    security_md_filename: str

CATEGORY = "security_md"
DEFAULT_CONFIG: DefaultConfig = {
    "security_md_filename" : "SECURITY.MD"
}

LANGUAGES = [ "ALL" ]

def check_security_md_exists(repo: RepoLinter) -> None:
    """ checks that SECURITY.md exists """

    repo.skip_on_archived()

    if repo.cached_get_file(repo.config[CATEGORY]["security_md_filename"]) is None:
        repo.error(CATEGORY, "File SECURITY.md is missing or empty")

def fix_create_security_md(repo: RepoLinter) -> None:
    """ creates a templated SECURITY.md file """

    filename = repo.config[CATEGORY]["security_md_filename"]

    repo.skip_on_archived()

    existing_file = repo.cached_get_file(filename)

    if existing_file is None:

        security_md_file = generate_jinja2_template_file(
            module=CATEGORY,
            filename=filename,
            context = {
                "repo_name" : repo.repository.name,
            }
        )
        if security_md_file is None:
            repo.error(CATEGORY, "Failed to generate {filename}")
            return None

        logger.debug(security_md_file)
        message = f"Created {filename}"

        result = repo.create_or_update_file(
            filepath=filename,
            newfile=security_md_file,
            oldfile=existing_file,
            message=f"dependabot - {CATEGORY} - {message}"
        )
        if result is not None:
            repo.fix(CATEGORY, f"{message} - commit {result}")
        else:
            logger.debug("File {} wasn't updated.", filename)
    else:
        logger.debug("Skipping creation of SECURITY.md, file exists...")
    return None
