"""pyproject.toml checks"""

import json
import re

from typing import Any, Dict, List, TypedDict

# from github.Repository import Repository

from loguru import logger  # type: ignore
import tomli_w

from github_linter.exceptions import NoChangeNeeded


from ..repolinter import RepoLinter

CATEGORY = "pyproject"
LANGUAGES = ["python"]

# Config Defintiion
DefaultConfig = TypedDict(
    "DefaultConfig",
    {
        "build-system": List[str],
        "readme": str,
    },
)

DEFAULT_CONFIG: DefaultConfig = {
    "build-system": [
        "flit_core.buildapi",  # flit
        "poetry.core.masonry.api",  # poetry
    ],
    "readme": "README.md",
}


def validate_pyproject_authors(
    repo: RepoLinter,
    project_object: Dict[str, Any],
) -> None:
    """checks the authors exist and are valid"""

    config_expected = repo.config.get("pyproject.toml")
    if "authors" not in project_object:
        repo.error(CATEGORY, "No authors in project definition.")

    elif config_expected and config_expected.get("authors"):
        for author in project_object["authors"]:
            if author not in config_expected.get("authors"):
                repo.error(CATEGORY, f"Project author not expected: {author}")
    else:
        for author in project_object["authors"]:
            repo.warning(CATEGORY, f"Check author is expected: {author}")


# pylint: disable=unused-argument
def validate_project_name(
    repo: RepoLinter,
    project_object: Dict[str, Any],
) -> bool:
    """validates that the project name matches the repo name"""

    if "name" not in project_object:
        repo.error(CATEGORY, "No 'name' field in [project] section of config")
        return False

    project_name = project_object["name"]
    if project_name != repo.repository.name:
        repo.error(
            CATEGORY,
            f"Project name doesn't match repo name repo: {repo.repository.name} project: {project_name}.",
        )
        return False
    return True


def validate_readme_configured(
    repo: RepoLinter,
    project_object: Dict[str, Any],
) -> bool:
    """validates that the project has a readme configured"""
    if "readme" not in project_object:
        repo.error(CATEGORY, "No 'readme' field in [project] section of config")
        return False

    expected_readme = repo.config[CATEGORY]["readme"]

    project_readme = project_object["readme"]
    if project_readme != expected_readme:
        repo.error(
            CATEGORY,
            f"Readme invalid - should be {expected_readme}, is {project_readme}",
        )
        return False
    return True


def validate_scripts(
    repo: RepoLinter,
    project_object: Dict[str, Any],
) -> bool:
    """validates that the project has a readme configured"""

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


def check_pyproject_build_backend(repo: RepoLinter) -> None:
    """gets the pyproject.toml file and looks for the key build-system.build-backend"""
    pyproject = repo.load_pyproject()

    if not pyproject:
        logger.error("pyproject.toml not found")
        return None

    if "build-system" not in pyproject:
        logger.error("Can't find build_backend")
        logger.debug(json.dumps(pyproject, indent=4, ensure_ascii=False))
        return None
    if "build-backend" not in pyproject["build-system"]:
        logger.error("Can't find build-system.build-backend.")
        logger.debug(json.dumps(pyproject["build-system"], indent=4, ensure_ascii=False))
        return None

    backend = pyproject["build-system"]["build-backend"]

    logger.warning("Found build-backend.build-system in pyproject.toml: {}", backend)
    return None


def check_pyproject_toml(
    repo: RepoLinter,
) -> None:
    """checks the data for the pyproject.toml file"""

    # config_expected = repo.config.get(CATEGORY)

    parsed = repo.load_pyproject()
    if not parsed:
        return repo.error(CATEGORY, "Failed to parse pyproject.toml")
    if not parsed.get("project"):
        return repo.error(CATEGORY, "No Project Section in file?")
    project = parsed["project"]

    # check the authors are expected
    # TODO: make this its own check
    validate_pyproject_authors(repo, project)
    # TODO: make this its own check
    validate_project_name(repo, project)

    if "urls" in project:
        for url in project["urls"]:
            logger.debug("URL: {} - {}", url, project["urls"][url])
    return None


# TODO: moving away from flit, don't need this
# def check_sdist_exclude_list(
#     repo: RepoLinter,
# ) -> None:
#     """ check for file exclusions so flit doesn't package things it shouldn't """
#     pyproject = load_pyproject()

#     if not pyproject:
#         repo.error(
#             CATEGORY,
#             "Failed to load pyproject.toml",
#         )
#         logger.error("Failed to find pyproject.toml")
#         return
#     sdist_exclude_list = [
#         "requirements*.txt",
#         ".gitignore",
#         ".pylintrc",
#         "*.json.example*",
#         "test_*.py",
#         "*.sh",
#         ".github/",
#         ".vscode/",
#         "*.json",
#         "mypy.ini",
#     ]

#     if "tool" not in pyproject:
#         repo.error(CATEGORY, "tool section not in config")
#         return
#     if "flit" not in pyproject["tool"]:
#         repo.error(CATEGORY, "tool.flit section not in config")
#         return
#     if "sdist" not in pyproject["tool"]["flit"]:
#         repo.error(CATEGORY, "tool.flit.sdist.exclude section not in config")
#         return
#     if "exclude" not in pyproject["tool"]["flit"]["sdist"]:
#         repo.error(CATEGORY, "tool.flit.sdist.exclude section not in config")
#         return

#     flit_exclude_list = pyproject["tool"]["flit"]["sdist"]["exclude"]

#     logger.debug(
#         json.dumps(flit_exclude_list, indent=4, default=str, ensure_ascii=False)
#     )

#     for entry in sdist_exclude_list:
#         if entry not in flit_exclude_list:
#             repo.error(CATEGORY, f"tool.flit.sdist section missing '{entry}' entry.")
#     return


def transfer_poetry_field(
    repo: RepoLinter,
    fieldname: str,
    poetry: Dict[str, Any],
    project: Dict[str, Any],
) -> None:
    """copy tool.poetry fields into the project section of pyproject.toml"""
    logger.debug(f"checking {fieldname=}")
    if fieldname in poetry:
        if fieldname not in project or project[fieldname] != poetry[fieldname]:
            if project.get(fieldname) != poetry[fieldname]:
                repo.fix(
                    CATEGORY,
                    f"Project {fieldname} didn't match, was {project.get(fieldname, 'unset')}, is now {poetry[fieldname]}",
                )
                project[fieldname] = poetry[fieldname]


def transfer_poetry_authors(
    repo: RepoLinter,
    poetry: Dict[str, Any],
    project: Dict[str, Any],
) -> None:
    """transfers authors"""

    if "authors" not in project:
        project["authors"] = []

    re_poetry_author = re.compile(r"(?P<name>[^\<]+) \<(?P<email>[^\>]+)\>$")
    for author in poetry["authors"]:
        results = re_poetry_author.search(author)

        if not results:
            continue
        details = results.groupdict()
        logger.debug(json.dumps(details))
        if details not in project["authors"]:
            project["authors"].append(details)
            repo.fix(
                CATEGORY,
                f"Transferred the following author from poetry to pyproject: {details}",
            )


def fix_copy_poetry_to_project(repo: RepoLinter) -> None:
    """fix tool.poetry fields into the project section of pyproject.toml

    PEP621 says a dict of name / email https://www.python.org/dev/peps/pep-0621/#authors-maintainers

    poetry:  Authors must be in the form name <email>.
    """
    # this pulls name/email from a poetry author
    pyproject = repo.load_pyproject()

    if not pyproject:
        repo.error(
            CATEGORY,
            "fix_copy_poetry_to_project failed - attempted to fix pyproject but doesn't exist",
        )
        return

    # check the name field

    if "tool" not in pyproject:
        logger.debug("tool not in pyproject, bailing")
        return

    if "poetry" not in pyproject["tool"]:
        logger.debug("tool.poetry not in pyproject, bailing")
        return

    poetry = pyproject["tool"]["poetry"]

    if "project" not in pyproject:
        pyproject["project"] = {}
    project = pyproject["project"]

    for field in [
        "name",
        "description",
        "license",
        "version",
        "readme",
        "homepage",
        "documentation",
        "repository",
        "keywords",
        "classifiers",
        # TODO: Check how this maps to pyproject.toml
        # "packages",
    ]:
        transfer_poetry_field(repo, field, poetry, project)

    # TODO: maintainers, similar to authors
    if "authors" in poetry:
        transfer_poetry_authors(repo, poetry, project)

    newfilecontents = tomli_w.dumps(pyproject)
    logger.debug("Updated pyproject.toml:")
    logger.debug(newfilecontents)

    filecontents = repo.cached_get_file("pyproject.toml", clear_cache=True)
    if filecontents and newfilecontents != filecontents.decoded_content.decode("utf-8"):
        commit = repo.create_or_update_file(
            "pyproject.toml",
            newfile=newfilecontents,
            oldfile=filecontents,
            message="github-linter.fix_copy_poetry_to_project updating pyproject.toml",
        )
        repo.fix(CATEGORY, f"fixed pyproject.toml - commit url {commit}")
    else:
        logger.debug("pyproject.toml is up to date")

    # TODO: copy the scripts settings around
    # [tool.poetry.scripts]
    # poetry = 'poetry.console:run'
    # TODO: include and exclude fields from poetry should match sdist from flit?

    # TODO: tools.poetry.urls (arbitrary URLs) https://python-poetry.org/docs/pyproject/#urls


def check_mypy_pydantic_plugin(repo: RepoLinter) -> None:
    """checks that the pydantic plugin's enabled for mypy"""

    # [tool.mypy]
    # plugins = "pydantic.mypy"
    repo.skip_on_archived()
    pyproject = repo.load_pyproject()
    pyproject_file = repo.cached_get_file("pyproject.toml")

    if pyproject is None or pyproject_file is None:
        logger.info("No pyproject file found in repo {}", repo.repository.full_name)
        raise NoChangeNeeded

    if not any(line for line in str(pyproject_file.decoded_content.decode("utf-8")).split("\n") if line.strip().startswith("mypy")):
        logger.info("mypy not found in pyproject.toml")
        raise NoChangeNeeded

    if not any(line for line in str(pyproject_file.decoded_content.decode("utf-8")).split("\n") if line.strip().startswith("pydantic")):
        logger.info("pydantic not found in pyproject.toml")
        raise NoChangeNeeded

    if "tool" not in pyproject:
        repo.error(CATEGORY, "section 'tool' not found while checking for mypy pydantic plugin")
        return
    if "mypy" not in pyproject["tool"]:
        repo.error(
            CATEGORY,
            "section 'tool.mypy' not found while checking for mypy pydantic plugin",
        )
        return
    if "plugins" not in pyproject["tool"]["mypy"]:
        repo.error(
            CATEGORY,
            "section 'tool.mypy.plugins' not found while checking for mypy pydantic plugin",
        )
        return
    if "pydantic.mypy" not in pyproject["tool"]["mypy"]["plugins"]:
        repo.error(CATEGORY, "section 'tool.mypy.plugins' does not contain pydantic.mypy")
        return


def fix_mypy_pydantic_plugin(repo: RepoLinter) -> None:
    """ensures that the pydantic plugin's enabled for mypy"""
    repo.skip_on_archived()
    try:
        check_mypy_pydantic_plugin(repo)
    except NoChangeNeeded:
        logger.debug("No change needed for fix_mypy_pydantic_plugin")
        return None
    pyproject = repo.load_pyproject()
    pyproject_file = repo.cached_get_file("pyproject.toml")
    if pyproject is None or pyproject_file is None:
        logger.info("No pyproject file found in repo {}", repo.repository.full_name)
        return

    if "tool" not in pyproject:
        pyproject["tool"] = {}

    if "mypy" not in pyproject["tool"]:
        pyproject["tool"]["mypy"] = {}

    if "plugins" not in pyproject["tool"]["mypy"]:
        pyproject["tool"]["mypy"]["plugins"] = "pydantic.mypy"

    logger.debug(tomli_w.dumps(pyproject))
    result = repo.create_or_update_file(
        "pyproject.toml",
        tomli_w.dumps(pyproject),
        repo.cached_get_file("pyproject.toml"),
        "Added pydantic plugin to mypy config in pyproject.toml",
    )
    logger.success("Added pydantic plugin to mypy config in pyproject.toml {}", result)
