""" checks for dependabot config """

from configparser import ConfigParser, NoOptionError #, NoSectionError
from typing import Optional

import json5 as json
from loguru import logger

from github_linter import RepoLinter



CATEGORY = "pylintrc"

LANGUAGES = ["python"]

# https://pylint.pycqa.org/en/latest/user_guide/run.html
PYLINTRC_LOCATIONS = [
    "pylintrc",
    ".pylintrc",
    # "pyproject.toml" # providing it has at least one tool.pylint. section
    # "setup.cfg" # needs pylint.*
]


def load_pylintrc(repo: RepoLinter) -> Optional[ConfigParser]:
    """ grabs the .pylintrc file from the repository """

    for filepath in PYLINTRC_LOCATIONS:
        contents = repo.cached_get_file(filepath)
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
    config: Optional[ConfigParser] = load_pylintrc(repo)

    if not config:
        repo.add_warning(CATEGORY, ".pylintrc not found")
        return
    if "MASTER" not in config.sections():
        logger.debug("Can't find MASTER entry, dumping config")
        logger.debug(json.dumps(config, indent=4, default=str, ensure_ascii=False))
        return
    try:
        linelength = config.get("MASTER", "max-line-length")
    except NoOptionError:
        repo.add_warning(CATEGORY, "max-line-length not configured")
        return


    # default setting
    expected = 100
    if "pylintrc" in repo.config:
        if "max-line-length" in repo.config[CATEGORY]:
            expected = repo.config[CATEGORY]["max-line-length"]

    if int(linelength) != int(expected):
        repo.add_error(
            CATEGORY,
            f"max-line-length wrong, is {linelength}, should be {expected}",
            )
    return


def check_pylintrc(
    repo: RepoLinter,
):
    """ checks for .pylintrc config """

    pylintrc = repo.cached_get_file(".pylintrc")

    if not pylintrc:
        repo.add_warning(CATEGORY, ".pylintrc not found")
