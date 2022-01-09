""" pyproject.toml checks """

import json

# from typing import List, Dict

from github.Repository import Repository

# from github.GithubException import UnknownObjectException
from loguru import logger
import tomli

from .. import GithubLinter
from ..types import DICTLIST
from ..utils import add_result, get_file_from_repo

CATEGORY = "pyproject.toml"


def validate_pyproject_authors(
    github_object: GithubLinter,
    project_object: dict,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> None:
    """ checks the authors exist and are valid """

    config_expected = github_object.config.get("pyproject.toml")
    if "authors" not in project_object:
        add_result(errors_object, CATEGORY, "No authors in project definition.")

    elif config_expected and config_expected.get("authors"):
        for author in project_object["authors"]:
            if author not in config_expected.get("authors"):
                add_result(
                    errors_object, CATEGORY, f"Project author not expected: {author}"
                )
    else:
        for author in project_object["authors"]:
            add_result(warnings_object, CATEGORY, f"Check author is expected: {author}")


def check_pyproject_toml(
    github_object: GithubLinter,
    repo_object: Repository,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> None:
    """ checks the data for the pyproject.toml file """
    fileresult = get_file_from_repo(repo_object, "pyproject.toml")
    if not fileresult:
        return

    # config_expected = github_object.config.get(CATEGORY)

    try:
        parsed = tomli.loads(fileresult.decoded_content.decode("utf-8"))
    except tomli.TOMLDecodeError as tomli_error:
        logger.debug(
            "Failed to parse {}/pyproject.toml: {}", repo_object.full_name, tomli_error
        )
        add_result(
            errors_object, CATEGORY, f"Failed to parse pyproject.toml: {tomli_error}"
        )
        return
    logger.debug(json.dumps(parsed, indent=4, ensure_ascii=False))

    if not parsed.get("project"):
        add_result(errors_object, CATEGORY, "No Project Section in file?")
    else:
        project = parsed["project"]

        # check the authors are expected
        validate_pyproject_authors(github_object, project, errors_object, warnings_object)
        for url in project.get("urls"):
            logger.debug("URL: {} - {}", url, project["urls"][url])
    return
