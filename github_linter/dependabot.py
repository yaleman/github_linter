""" checks for dependabot config """

import json
from typing import Dict, List

from loguru import logger
from github.Repository import Repository
import yaml

# from . import GithubLinter
from .utils import add_result, get_file_from_repo

# template = """
# version: 2
# updates:
# - package-ecosystem: pip
#   directory: "/"
#   schedule:
#     interval: daily
#     time: "06:00"
#     timezone: Australia/Brisbane
#   open-pull-requests-limit: 99
# """

CONFIG = {
    "version" : "2",
    "updates" : [
        {
            "directory" : "/",
            "schedule" : {
                "interval" : "daily",
                "time" : "06:00",
                "timezone" : "Australia/Brisbane"
            }
        }
    ],
    "open-pull-requests-limit" : 99
}


CATEGORY = "dependabot"

def check_dependabot_config(
    repo: Repository,
    errors_object: Dict[str, List[str]],
    _: Dict[str, List[str]],
    ):
    """ checks for dependabot config """

    fileresult = get_file_from_repo(repo, ".github/dependabot.yml")
    if not fileresult:
        logger.debug("Couldn't find dependabot config.")
        return

    try:
        dependabot_config = yaml.safe_load(fileresult.decoded_content.decode("utf-8"))
    except yaml.YAMLError as exc:
        logger.error("Failed to parse dependabot config: {}", exc)
        add_result(errors_object, CATEGORY, f"Failed to parse dependabot config: {exc}")
        return
    logger.debug(json.dumps(dependabot_config, indent=4, default=str, ensure_ascii=False))
    return
