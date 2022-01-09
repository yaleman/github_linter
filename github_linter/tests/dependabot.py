""" checks for dependabot config """

import json
from typing import Dict, List, Union, TypedDict

from loguru import logger
from github.Repository import Repository
import pytz
import yaml

from github_linter import GithubLinter

# from . import GithubLinter
from ..types import DICTLIST
from ..utils import add_result, get_file_from_repo

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

CATEGORY = "dependabot"
LANGUAGES = [
    "all",
]

CONFIG = {
    "version": "2",
    "updates": [
        {
            "directory": "/",
            "schedule": {
                "interval": "daily",
                "time": "06:00",
                "timezone": "Australia/Brisbane",
            },
        }
    ],
    "open-pull-requests-limit": 99,
}


DEPENDABOT_CONFIG_FILE = TypedDict(
    "DEPENDABOT_CONFIG_FILE",
    {
        "version": int,
        "updates": List[Dict[str, str]],
    },
)

VALID_VALUES = {
    "package-ecosystem": {
        "bundler" : [] ,
        "cargo" : [],
        "composer" : [],
        "docker" : [],
        "mix" : [],
        "elm" : [],
        "gitsubmodule" : [],
        "github-actions" : [],
        "gomod" : [],
        "gradle" : [],
        "maven" : [],
        "npm" : [],
        "nuget" : [],
        "pip" : ["Python"],
        "terraform" : [],
    }
}


 # TODO: base dependabot config on repo.get_languages() - ie {'Python': 22722, 'Shell': 328}

def validate_update_config(
    updates,
    error_object: DICTLIST,
    _: DICTLIST,  # warnings_object
):
    """ checks update config """
    for update in updates:
        logger.debug(json.dumps(update, indent=4))
        if "package-ecosystem" not in update:
            add_result(error_object, CATEGORY, "package-ecosystem not set in an update")
        elif (
            update["package-ecosystem"] not in VALID_VALUES["package-ecosystem"]
        ):
            add_result(
                error_object,
                CATEGORY,
                f"package-ecosystem set to invalid value: '{update['package-ecosystem']}'",
            )
        if "schedule" in update:
            if "timezone" in update["schedule"]:
                if update["schedule"]["timezone"] not in pytz.all_timezones:
                    add_result(
                        error_object,
                        CATEGORY,
                        f"Update timezone's not valid? {update['schedule']['timezone']}",
                    )


def load_file(
    repo: Repository,
    errors_object: DICTLIST,
    _: DICTLIST,
) -> Union[Dict, DEPENDABOT_CONFIG_FILE]:
    """ grabs the config file and loads it """
    fileresult = get_file_from_repo(repo, ".github/dependabot.yml")
    if not fileresult:
        logger.debug("Couldn't find dependabot config.")
        return {}

    try:
        dependabot_config = yaml.safe_load(fileresult.decoded_content.decode("utf-8"))
        logger.debug(
            json.dumps(dependabot_config, indent=4, default=str, ensure_ascii=False)
        )
        return dependabot_config
    except yaml.YAMLError as exc:
        logger.error("Failed to parse dependabot config: {}", exc)
        add_result(errors_object, CATEGORY, f"Failed to parse dependabot config: {exc}")
    return {}


def check_dependabot_config(
    _: GithubLinter,
    repo: Repository,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
):
    """ checks for dependabot config """

    dependabot_config = load_file(repo, errors_object, warnings_object)

    if not dependabot_config:
        add_result(warnings_object, CATEGORY, "No dependabot configuration found.")
        return

    if "updates" in dependabot_config:
        validate_update_config(
            dependabot_config["updates"], errors_object, warnings_object
        )
