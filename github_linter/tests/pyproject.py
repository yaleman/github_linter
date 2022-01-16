""" pyproject.toml checks """

import json

from typing import List, TypedDict
# from github.Repository import Repository

from loguru import logger
import tomli

from .. import RepoLinter

CATEGORY = "pyproject.toml"
LANGUAGES = ["python"]

# Config Defintiion
DefaultConfig = TypedDict("DefaultConfig",
{
    "build-system": List[str],
    "readme": str,

})

DEFAULT_CONFIG: DefaultConfig = {
    "build-system" : [
        "flit_core.buildapi",      # flit
        "poetry.core.masonry.api", # poetry
    ],
    "readme" : "README.md",
}

def validate_pyproject_authors(
    repo: RepoLinter,
    project_object: dict,

) -> None:
    """ checks the authors exist and are valid """

    config_expected = repo.config.get("pyproject.toml")
    if "authors" not in project_object:
        repo.error( CATEGORY, "No authors in project definition.")

    elif config_expected and config_expected.get("authors"):
        for author in project_object["authors"]:
            if author not in config_expected.get("authors"):
                repo.error(CATEGORY, f"Project author not expected: {author}"
                )
    else:
        for author in project_object["authors"]:
            repo.warning(CATEGORY, f"Check author is expected: {author}")


# pylint: disable=unused-argument
def validate_project_name(
    repo: RepoLinter,
    project_object: dict,
) -> bool:
    """ validates that the project name matches the repo name """

    if "name" not in project_object:
        repo.error(CATEGORY, "No 'name' field in [project] section of config"
        )
        return False

    project_name = project_object["name"]
    if project_name != repo.repository.name:
        repo.error(CATEGORY,
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
        repo.error(CATEGORY, "No 'readme' field in [project] section of config"
        )
        return False

    expected_readme = repo.config[CATEGORY]["readme"]

    project_readme = project_object["readme"]
    if project_readme != expected_readme:
        repo.error(CATEGORY,
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
        logger.debug("No scripts configured in pyproject.toml")
        return False
    retval = True
    for script in project_object["scripts"]:
        script_def = project_object["scripts"][script]
        script_def_module = script_def.split(".")[0]
        if script_def_module != repo.repository.name:
            repo.error(
                CATEGORY,
                f"Script has invalid module: expected {repo.repository.name}, found {script_def_module}",
            )
        # check it's pulling from __main__
        if len(script_def_module.split(".") > 1):
            if script_def_module.split(".")[1].split(":") != "__main__":
                repo.error(
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

def check_pyproject_build_backend(repo: RepoLinter):
    """ gets the pyproject.toml file and looks for the key build-system.build-backend """
    pyproject = load_pyproject(repo)

    if not pyproject:
        logger.error("pyproject.toml not found")
        return

    if "build-system" not in pyproject:
        logger.error("Can't find build_backend")
        logger.debug(json.dumps(pyproject, indent=4, ensure_ascii=False))
        return
    if "build-backend" not in pyproject["build-system"]:
        logger.error("Can't find build-system.build-backend.")
        logger.debug(json.dumps(pyproject["build-system"], indent=4, ensure_ascii=False))
        return

    backend = pyproject["build-system"]["build-backend"]

    logger.warning("Found build-backend.build-system in pyproject.toml: {}", backend)
    # logger.info()
    return

def check_pyproject_toml(
    repo: RepoLinter,
) -> None:
    """ checks the data for the pyproject.toml file """

    # config_expected = repo.config.get(CATEGORY)

    parsed = load_pyproject(repo)
    if not parsed:
        return repo.error(CATEGORY, "Failed to parse pyproject.toml")
    if not parsed.get("project"):
        return repo.error(CATEGORY, "No Project Section in file?")
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

    if "urls" in project:
        for url in project["urls"]:
            logger.debug("URL: {} - {}", url, project["urls"][url])
    return None
# need to check for file exclusions so flit doesn't package things


def check_sdist_exclude_list(
    repo: RepoLinter,
) -> None:
    """ check for file exclusions so flit doesn't package things it shouldn't """
    pyproject = load_pyproject(repo)

    if not pyproject:
        repo.error(CATEGORY,
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
        repo.error(CATEGORY, "tool section not in config")
        return
    if "flit" not in pyproject["tool"]:
        repo.error(CATEGORY, "tool.flit section not in config")
        return
    if "sdist" not in pyproject["tool"]["flit"]:
        repo.error(CATEGORY, "tool.flit.sdist.exclude section not in config")
        return
    if "exclude" not in pyproject["tool"]["flit"]["sdist"]:
        repo.error(CATEGORY, "tool.flit.sdist.exclude section not in config")
        return

    flit_exclude_list = pyproject["tool"]["flit"]["sdist"]["exclude"]

    logger.debug(json.dumps(flit_exclude_list, indent=4, default=str, ensure_ascii=False))


    for entry in sdist_exclude_list:
        if entry not in flit_exclude_list:
            repo.error(CATEGORY,
                f"tool.flit.sdist section missing '{entry}' entry.")
    return
