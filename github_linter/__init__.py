""" goes through your repos and checks for things """

from json.decoder import JSONDecodeError
import os
from pathlib import Path
from typing import Union, Dict

import json5 as json  # type: ignore
from loguru import logger
from github import Github

__version__ = "0.0.1"


def load_config() -> Union[Dict[str, str], bool]:
    """ loads config """
    for configfile in [
        Path("./github_linter.json"),
        Path(os.path.expanduser("~/.config/github_linter.json")),
    ]:
        if not configfile.exists():
            continue
        try:
            config = json.load(configfile.open(encoding="utf8"))
            logger.debug("Using config file {}", configfile.as_posix())
            return config
        except JSONDecodeError as json_error:
            logger.error("Failed to load {}: {}", configfile.as_posix(), json_error)
    logger.error("Failed to find config file")
    return False


# pylint: disable=too-few-public-methods
class GithubLinter:
    """ does things """

    def __init__(self):
        """ setup """
        if os.getenv("GITHUB_TOKEN"):
            logger.debug("Using GITHUB_TOKEN")
            self.github = Github(os.getenv("GITHUB_TOKEN"))

        self.config = load_config()
        if not self.config:
            self.config = {}

        self.report = {}

    def display_report(self):
        """ displays a report """
        for repo_name in self.report:
            repo = self.report[repo_name]
            if not repo:
                logger.warning("Empty report for {}, skipping", repo_name)
            errors = []
            warnings = []
            if "errors" in repo and repo["errors"]:
                for category in repo["errors"]:
                    if repo["errors"][category]:
                        errors = [f" - {error}" for error in repo["errors"][category]]
            if "warnings" in repo and repo["warnings"]:
                for category in repo["warnings"]:
                    if repo["warnings"][category]:
                        warnings = [
                            f" - {warning}" for warning in repo["warnings"][category]
                        ]
            if errors or warnings:
                logger.info("Report for {}", repo_name)
                for error in errors:
                    logger.error(error)
                for warning in warnings:
                    logger.warning(warning)
            else:
                logger.info("Repository {} checks out OK", repo_name)
