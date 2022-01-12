""" pyproject.toml checks """

import json

# from typing import List, Dict

# from github.Repository import Repository

from loguru import logger
import tomli

from .. import RepoLinter

CATEGORY = "pyproject.toml"
LANGUAGES = ["python"]


def validate_pyproject_authors(
    repo: RepoLinter,
    project_object: dict,

) -> None:
    """ checks the authors exist and are valid """

    config_expected = repo.config.get("pyproject.toml")
    if "authors" not in project_object:
        repo.add_error( CATEGORY, "No authors in project definition.")

    elif config_expected and config_expected.get("authors"):
        for author in project_object["authors"]:
            if author not in config_expected.get("authors"):
                repo.add_error(CATEGORY, f"Project author not expected: {author}"
                )
    else:
        for author in project_object["authors"]:
            repo.add_warning(CATEGORY, f"Check author is expected: {author}")


# pylint: disable=unused-argument
def validate_project_name(
    repo: RepoLinter,
    project_object: dict,
) -> bool:
    """ validates that the project name matches the repo name """

    if "name" not in project_object:
        repo.add_error(CATEGORY, "No 'name' field in [project] section of config"
        )
        return False

    project_name = project_object["name"]
    if project_name != repo.repository.name:
        repo.add_error(CATEGORY,
            f"Project name doesn't match repo name repo: {repo.repository.name} project: {project_name}.",
        )
        return False
    return True



def validate_readme_configured(
    repo: RepoLinter,
    project_object: dict,
) -> bool:
    """ validates that the project has a readme configured """
    if "readme" not in project_object:
        repo.add_error(CATEGORY, "No 'readme' field in [project] section of config"
        )
        return False

    if (
        "pyproject" not in repo.config
        or "readme" not in repo.config["pyproject"]
    ):
        expected_readme = "README.md"
    else:
        expected_readme = repo.config["pyproject"]["readme"]

    project_readme = project_object["readme"]
    if project_readme != expected_readme:
        repo.add_error(CATEGORY,
            f"Readme invalid - should be {expected_readme}, is {project_readme}",
        )
        return False
    return True


def validate_scripts(
    repo: RepoLinter,
    project_object: dict,
) -> bool:
    """ validates that the project has a readme configured """

    if "scripts" not in project_object:
        # repo.add_error( CATEGORY, "No 'readme' field in [project] section of config")
        logger.debug("No scripts configured in pyproject.toml")
        return False
    retval = True
    for script in project_object["scripts"]:
        script_def = project_object["scripts"][script]
        script_def_module = script_def.split(".")[0]
        if script_def_module != repo.repository.name:
            repo.add_error(
                CATEGORY,
                f"Script has invalid module: expected {repo.repository.name}, found {script_def_module}",
            )
        # check it's pulling from __main__
        if len(script_def_module.split(".") > 1):
            if script_def_module.split(".")[1].split(":") != "__main__":
                repo.add_error(
                    CATEGORY,
                    f"Script has invalid module: expected __main__, found {script_def_module}",
                )
                retval = False
    return retval

def load_pyproject(repo: RepoLinter):
    """ loads the pyproject.toml file """

    fileresult = repo.cached_get_file("pyproject.toml")
    if not fileresult:
        logger.debug("No content for pyproject.toml")
        return None

    try:
        return tomli.loads(fileresult.decoded_content.decode("utf-8"))
    except tomli.TOMLDecodeError as tomli_error:
        logger.debug(
            "Failed to parse {}/pyproject.toml: {}", repo.repository.full_name, tomli_error
        )
        return None
    return None

def check_pyproject_toml(
    repo: RepoLinter,
) -> None:
    """ checks the data for the pyproject.toml file """

    # config_expected = repo.config.get(CATEGORY)

    parsed = load_pyproject(repo)
    if not parsed:
        return repo.add_error(CATEGORY, "Failed to parse pyproject.toml")
    if not parsed.get("project"):
        return repo.add_error(CATEGORY, "No Project Section in file?")
    project = parsed["project"]

    # check the authors are expected
    # TODO: make this its own check
    validate_pyproject_authors(
        repo, project
    )
    # TODO: make this its own check
    validate_project_name(
        repo, project
    )

    for url in project.get("urls"):
        logger.debug("URL: {} - {}", url, project["urls"][url])
    return None
# need to check for file exclusions so flit doesn't package things


def check_sdist_exclude_list(
    repo: RepoLinter,
) -> None:
    """ check for file exclusions so flit doesn't package things it shouldn't """
    pyproject = load_pyproject(repo)

    if not pyproject:
        repo.add_error(CATEGORY,
            "Failed to load pyproject.toml",
        )
        logger.error("Failed to find pyproject.toml")
        return
    sdist_exclude_list = [
        "requirements*.txt",
        ".gitignore",
        ".pylintrc",
        "*.json.example*",
        "test_*.py",
        "*.sh",
        ".github/",
        ".vscode/",
        "*.json",
        "mypy.ini",
    ]


    if "tool" not in pyproject:
        repo.add_error(CATEGORY, "tool section not in config")
        return
    if "flit" not in pyproject["tool"]:
        repo.add_error(CATEGORY, "tool.flit section not in config")
        return
    if "sdist" not in pyproject["tool"]["flit"]:
        repo.add_error(CATEGORY, "tool.flit.sdist.exclude section not in config")
        return
    if "exclude" not in pyproject["tool"]["flit"]["sdist"]:
        repo.add_error(CATEGORY, "tool.flit.sdist.exclude section not in config")
        return

    flit_exclude_list = pyproject["tool"]["flit"]["sdist"]["exclude"]

    logger.debug(json.dumps(flit_exclude_list, indent=4, default=str, ensure_ascii=False))


    for entry in sdist_exclude_list:
        if entry not in flit_exclude_list:
            repo.add_error(CATEGORY,
                f"tool.flit.sdist section missing '{entry}' entry.")
    return
