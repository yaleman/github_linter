""" pyproject.toml checks """

import json

# from typing import List, Dict

# from github.Repository import Repository

from loguru import logger
import tomli

from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..types import DICTLIST
from ..utils import add_result

CATEGORY = "pyproject.toml"
LANGUAGES = ["python"]


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


# pylint: disable=unused-argument
def validate_project_name(
    github_object: GithubLinter,
    project_object: dict,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> bool:
    """ validates that the project name matches the repo name """

    if not github_object.current_repo:
        raise RepositoryNotSet

    if "name" not in project_object:
        add_result(
            errors_object, CATEGORY, "No 'name' field in [project] section of config"
        )
        return False

    project_name = project_object["name"]
    if project_name != github_object.current_repo.name:
        add_result(
            errors_object,
            CATEGORY,
            f"Project name doesn't match repo name repo: {github_object.current_repo.name} project: {project_name}.",
        )
        return False
    return True



def validate_readme_configured(
    github_object: GithubLinter,
    project_object: dict,
    errors_object: DICTLIST,
    _: DICTLIST,
) -> bool:
    """ validates that the project has a readme configured """
    if "readme" not in project_object:
        add_result(
            errors_object, CATEGORY, "No 'readme' field in [project] section of config"
        )
        return False

    if (
        "pyproject" not in github_object.config
        or "readme" not in github_object.config["pyproject"]
    ):
        expected_readme = "README.md"
    else:
        expected_readme = github_object.config["pyproject"]["readme"]

    project_readme = project_object["readme"]
    if project_readme != expected_readme:
        add_result(
            errors_object,
            CATEGORY,
            f"Readme invalid - should be {expected_readme}, is {project_readme}",
        )
        return False
    return True


def validate_scripts(
    github_object: GithubLinter,
    project_object: dict,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> bool:
    """ validates that the project has a readme configured """

    if not github_object.current_repo:
        raise RepositoryNotSet
    if "scripts" not in project_object:
        # add_result(errors_object, CATEGORY, "No 'readme' field in [project] section of config")
        logger.debug("No scripts configured in pyproject.toml")
        return False
    retval = True
    for script in project_object["scripts"]:
        script_def = project_object["scripts"][script]
        script_def_module = script_def.split(".")[0]
        if script_def_module != github_object.current_repo.name:
            add_result(
                errors_object,
                CATEGORY,
                f"Script has invalid module: expected {github_object.current_repo.name}, found {script_def_module}",
            )
        # check it's pulling from __main__
        if len(script_def_module.split(".") > 1):
            if script_def_module.split(".")[1].split(":") != "__main__":
                add_result(
                    errors_object,
                    CATEGORY,
                    f"Script has invalid module: expected __main__, found {script_def_module}",
                )
                retval = False
    return retval


def check_pyproject_toml(
    github_object: GithubLinter,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
) -> None:
    """ checks the data for the pyproject.toml file """

    if not github_object.current_repo:
        raise RepositoryNotSet

    fileresult = github_object.cached_get_file("pyproject.toml")
    if not fileresult:
        return

    # config_expected = github_object.config.get(CATEGORY)

    try:
        parsed = tomli.loads(fileresult.decoded_content.decode("utf-8"))
    except tomli.TOMLDecodeError as tomli_error:
        logger.debug(
            "Failed to parse {}/pyproject.toml: {}", github_object.current_repo.full_name, tomli_error
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
        validate_pyproject_authors(
            github_object, project, errors_object, warnings_object
        )
        validate_project_name(
            github_object, project, errors_object, warnings_object
        )

        for url in project.get("urls"):
            logger.debug("URL: {} - {}", url, project["urls"][url])
    return
