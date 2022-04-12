""" checks for dependabot config """

from configparser import ConfigParser, NoOptionError  # , NoSectionError
from typing import List, Optional, TypedDict

# from jinja2 import Environment, PackageLoader, select_autoescape
# import jinja2.exceptions
import json5 as json
from loguru import logger

from github_linter.repolinter import RepoLinter

CATEGORY = "pylintrc"

LANGUAGES = ["python"]

# TODO: look in "/<repo.name>/.pylintrc"


class PylintRC(TypedDict):
    """ defines the settings for a pylintrc file """

    disable: List[str]
    max_line_length: Optional[int]


class DefaultConfig(TypedDict):
    """ config typing for module config """

    # https://pylint.pycqa.org/en/latest/user_guide/run.html
    pylintrc_locations: List[str]
    pylintrc: Optional[PylintRC]


DEFAULT_CONFIG: DefaultConfig = {
    # documentation for list of locations
    # https://pylint.pycqa.org/en/latest/user_guide/run.html?highlight=pylintrc#command-line-options
    "pylintrc_locations": [
        ".pylintrc",
        "pylintrc",
        # "pyproject.toml" # providing it has at least one tool.pylint. section
        # "setup.cfg" # needs pylint.*
    ],
    "pylintrc": None,
}


def load_pylintrc(repo: RepoLinter, clear_cache: bool = False) -> Optional[ConfigParser]:
    """ grabs the .pylintrc file from the repository """

    for filepath in repo.config[CATEGORY]["pylintrc_locations"]:
        contents = repo.cached_get_file(filepath, clear_cache)
        if not contents:
            continue

        config = ConfigParser()
        if not contents.content:
            return None
        config.read_string(contents.decoded_content.decode("utf-8"))
        logger.debug("Successfully loaded {}", filepath)
        return config
    return None


def check_max_line_length_configured(repo: RepoLinter) -> None:
    """ checks for the max-line-length setting in .pylintrc """

    # default setting
    if "pylintrc" in repo.config:
        if "max_line_length" not in repo.config[CATEGORY]:
            logger.debug("max_line_length not set in config, no need to run.")
            return

    config: Optional[ConfigParser] = load_pylintrc(repo)

    if not config:
        repo.warning(CATEGORY, ".pylintrc not found")
        return
    if "MASTER" not in config.sections():
        logger.debug("Can't find MASTER entry, dumping config")
        logger.debug(json.dumps(config, indent=4, default=str, ensure_ascii=False))
        return
    try:
        linelength = config.get("MASTER", "max-line-length")
    except NoOptionError:
        repo.warning(CATEGORY, "max-line-length not configured")
        return
    expected = repo.config[CATEGORY]["max_line_length"]

    if int(linelength) != int(expected):
        repo.error(
            CATEGORY,
            f"max-line-length wrong, is {linelength}, should be {expected}",
        )
    return


def check_pylintrc(
    repo: RepoLinter,
) -> None:
    """ checks for .pylintrc config """

    pylintrc = repo.cached_get_file(".pylintrc")

    if not pylintrc:
        repo.warning(CATEGORY, ".pylintrc not found")


def fix_pylintrc_missing(
    _: RepoLinter,
) -> None:
    """ if there's no .pylintrc at all, add one """

    logger.error("SKIPPING PYLINTRC UNTIL IT IS MOVED TO PYPROJECT - ref #73")
    # if not repo.config[CATEGORY]["pylintrc_locations"]:
    #     logger.debug(
    #         "pylintrc_locations has been set to an empty list, bailing on this fix."
    #     )
    #     return

    # if not repo.config[CATEGORY]["pylintrc"]:
    #     logger.debug("pylintrc not configured, bailing on this fix.")
    #     return

    # # check if the pylintrc file exists in any of the check places
    # for filepath in repo.config[CATEGORY]["pylintrc_locations"]:
    #     filecontents = repo.cached_get_file(filepath, clear_cache=True)
    #     if filecontents:
    #         logger.debug("File exists in {}, no action required.", filepath)
    #         return

    # filepath = repo.config[CATEGORY]["pylintrc_locations"][0]
    # logger.debug("Writing pylintrc file at: {}", filepath)

    # # start up jinja2
    # jinja2_env = Environment(
    #     loader=PackageLoader(package_name="github_linter", package_path="."),
    #     autoescape=select_autoescape(),
    # )
    # try:
    #     template = jinja2_env.get_template(f"fixes/{CATEGORY}/pylintrc")

    #     context = {}

    #     for key in repo.config[CATEGORY]["pylintrc"]:
    #         if repo.config[CATEGORY]["pylintrc"]:
    #             context[key] = repo.config[CATEGORY]["pylintrc"][key]

    #     new_filecontents = template.render(**context)

    # except jinja2.exceptions.TemplateNotFound as template_error:
    #     logger.error("Failed to load template: {}", template_error)
    # commit_url = repo.create_or_update_file(
    #     filepath=filepath,
    #     newfile=new_filecontents,
    #     message=f"github-linter pylintrc module creating {filepath}",
    # )
    # repo.fix(CATEGORY, f"Created {filepath}, commit url: {commit_url}")
