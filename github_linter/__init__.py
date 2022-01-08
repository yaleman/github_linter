""" goes through your repos and checks for things """

import json
from json.decoder import JSONDecodeError
import os
from pathlib import Path
from typing import Union, Dict

from loguru import logger
from github import Github

__version__ = "0.0.1"


def load_config() -> Union[Dict[str, str], bool]:
    """ loads config """
    configfile = Path(os.path.expanduser("~/.config/github_linter.json"))
    if not configfile.exists():
        logger.error("Failed to find config file: {}", configfile.as_posix)
    try:
        config = json.load(configfile.open(encoding="utf8"))
    except JSONDecodeError as json_error:
        logger.error("Failed to load {}: {}", configfile.as_posix, json_error)
        return False
    return config


#pylint: disable=too-few-public-methods
class GithubLinter:
    """ does things """

    def __init__(self):
        """ setup """
        if os.getenv("GITHUB_TOKEN"):
            logger.info("Using GITHUB_TOKEN")
            self.github = Github(os.getenv("GITHUB_TOKEN"))
            # self.user = self.github.get_user()
            # self.interested_owners = [self.user.login]
            # for org in self.user.get_orgs():
            #     self.interested_owners.append(org.login)

        self.config = load_config()
        if not self.config:
            self.config = {}


# using username and password
# TODO: config file things
# g = Github("user", "password")
