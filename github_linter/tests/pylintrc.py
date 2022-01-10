""" checks for dependabot config """

# import json
from typing import Optional

from configparser import ConfigParser

import json5 as json

from loguru import logger
from github.Repository import Repository

# import yaml

from github_linter import GithubLinter

# from . import GithubLinter
from ..types import DICTLIST
from ..utils import add_result, get_file_from_repo

CATEGORY = "pylintrc"

LANGUAGES = ["python"]

# https://pylint.pycqa.org/en/latest/user_guide/run.html
PYLINTRC_LOCATIONS = [
    "pylintrc",
    ".pylintrc",
    # "pyproject.toml" # providing it has at least one tool.pylint. section
    # "setup.cfg" # needs pylint.*
]


def load_pylintrc(repo: Repository) -> Optional[ConfigParser]:
    """ grabs the .pylintrc file from the repository """
    contents = get_file_from_repo(repo, ".pylintrc")
    if not contents:
        return None
    config = ConfigParser()
    if not contents.content:
        return None
    config.read_string(contents.decoded_content.decode("utf-8"))
    return config


def check_max_line_length_configured(
    github: GithubLinter,
    repo: Repository,
    errors_object: DICTLIST,  #
    warnings_object: DICTLIST,
):
    """ checks for the max-line-length setting in .pylintrc """
    config: Optional[ConfigParser] = load_pylintrc(repo)

    if not config:
        add_result(warnings_object, CATEGORY, ".pylintrc not found")
        return False
    if "MASTER" not in config.sections():
        logger.debug("Can't find MASTER entry, dumping config")
        logger.debug(json.dumps(config, indent=4, default=str, ensure_ascii=False))
    linelength = config.get("MASTER", "max-line-length")

    if not linelength:
        add_result(warnings_object, CATEGORY, "max-line-length not configured")
    expected = 100
    if "pylintrc" in github.config:
        if "max-line-length" in github.config[CATEGORY]:
            expected = github.config[CATEGORY]["max-line-length"]

    if int(linelength) != int(expected):
        add_result(
            errors_object,
            CATEGORY,
            f"max-line-length wrong, is {linelength}, should be {expected}",
        )
    return True


def check_pylintrc(
    _: GithubLinter,
    repo: Repository,
    __: DICTLIST,  #
    warnings_object: DICTLIST,
):
    """ checks for .pylintrc config """

    pylintrc = get_file_from_repo(repo, ".pylintrc")

    if not pylintrc:
        add_result(warnings_object, CATEGORY, ".pylintrc not found")
