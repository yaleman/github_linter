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
    _: Repository,
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

# pylint: disable=unused-argument
def validate_project_name(
    github_object: GithubLinter,
    repo_object: Repository,
    project_object: dict,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> bool:
    """ validates that the project name matches the repo name """
    if "name" not in project_object["project"]:
        add_result(errors_object, CATEGORY, "No 'name' field in [project] section of config")
        return False

    project_name = project_object["project"]["name"]
    if project_name != repo_object.name:
        add_result(
            errors_object,
            CATEGORY,
            f"Project name doesn't match repo name repo: {repo_object.name} project: {project_name}.")
        return False
    return True

# pylint: disable=unused-argument
def validate_readme_configured(
    github_object: GithubLinter,
    repo_object: Repository,
    project_object: dict,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> bool:
    """ validates that the project has a readme configured """
    if "readme" not in project_object["project"]:
        add_result(errors_object, CATEGORY, "No 'readme' field in [project] section of config")
        return False

    if "pyproject" not in github_object.config or "readme" not in github_object.config["pyproject"]:
        expected_readme = "README.md"
    else:
        expected_readme = github_object.config["pyproject"]["readme"]

    project_readme = project_object["project"]["readme"]
    if project_readme != expected_readme:
        add_result(
            errors_object,
            CATEGORY,
            f"Readme invalid - should be {expected_readme}, is {project_readme}")
        return False
    return True

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
        validate_pyproject_authors(github_object, repo_object, project, errors_object, warnings_object)
        validate_project_name(github_object, repo_object, project, errors_object, warnings_object)

        for url in project.get("urls"):
            logger.debug("URL: {} - {}", url, project["urls"][url])
    return

