""" checks for dependabot config """

import json
from typing import Dict, List

from loguru import logger
from github.Repository import Repository
import yaml

from github_linter import GithubLinter

# from . import GithubLinter
from .types import DICTLIST
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

# https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates

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

VALID_VALUES = {
    "package-ecosystem" : [
        "bundler",
        "cargo",
        "composer",
        "docker",
        "mix",
        "elm",
        "gitsubmodule",
        "github-actions",
        "gomod",
        "gradle",
        "maven",
        "npm",
        "nuget",
        "pip",
        "terraform",
        "npm",
    ]
}
def check_update_config(updates: List[Dict[str,str]],
    error_object: DICTLIST,
    _: DICTLIST,): # warnings_object
    """ checks update config """

    for update in updates:
        logger.debug(json.dumps(update, indent=4))
        if "package-ecosystem" not in update:
            add_result(error_object, CATEGORY, "package-ecosystem not set in an update")
        elif update.get("package-ecosystem","") not in VALID_VALUES["package-ecosystem"]:
            add_result(error_object, CATEGORY, f"package-ecosystem set to invalid value: '{update['package-ecosystem']}'")

def check_dependabot_config(
    _: GithubLinter,
    repo: Repository,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
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
    if dependabot_config.get("updates"):
        check_update_config(dependabot_config["updates"], errors_object, warnings_object)

    return
