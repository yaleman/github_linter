""" checks for dependabot config """

from configparser import ConfigParser, NoOptionError #, NoSectionError
from typing import List, Optional, TypedDict

import json5 as json
from loguru import logger

from github_linter import RepoLinter

CATEGORY = "pylintrc"

LANGUAGES = ["python"]

# TODO: look in "/<repo.name>/.pylintrc"

class DefaultConfig(TypedDict):
    """ config typing for module config """
    # https://pylint.pycqa.org/en/latest/user_guide/run.html
    pylintrc_locations: List[str]

DEFAULT_CONFIG: DefaultConfig = {
    "pylintrc_locations" : [
        "pylintrc",
        ".pylintrc",
        # "pyproject.toml" # providing it has at least one tool.pylint. section
        # "setup.cfg" # needs pylint.*
    ]
}



def load_pylintrc(repo: RepoLinter) -> Optional[ConfigParser]:
    """ grabs the .pylintrc file from the repository """

    for filepath in repo.config[CATEGORY]["pylintrc_locations"]:
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


    # default setting
    expected = 100
    if "pylintrc" in repo.config:
        if "max-line-length" in repo.config[CATEGORY]:
            expected = repo.config[CATEGORY]["max-line-length"]

    if int(linelength) != int(expected):
        repo.error(
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
        repo.warning(CATEGORY, ".pylintrc not found")
