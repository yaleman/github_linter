""" checks for dependabot config """

import json
from typing import Dict, List, Union, TypedDict, Optional

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

# CONFIG = {
#     "version": "2",
#     "updates": [
#         {
#             "directory": "/",
#             "schedule": {
#                 "interval": "daily",
#                 "time": "06:00",
#                 "timezone": "Australia/Brisbane",
#             },
#         }
#     ],
#     "open-pull-requests-limit": 99,
# }


DEPENDABOT_CONFIG_FILE = TypedDict(
    "DEPENDABOT_CONFIG_FILE",
    {
        "version": int,
        "updates": List[Dict[str, str]],
    },
)

PACKAGE_ECOSYSTEM : Dict[str, List[str]] = {
        "bundler" : [] ,
        "cargo" : [ "rust" ],
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
        "pip" : ["python"],
        "terraform" : [ "HCL" ],
}

def find_language_in_ecosystem(language: str) -> Optional[str]:
    """ checks to see if languages are in VALID_VALUES["package-ecosystem"] """
    for package in PACKAGE_ECOSYSTEM:
        lowerlang = [lang.lower() for lang in PACKAGE_ECOSYSTEM[package]]
        if language.lower() in lowerlang:
            return package
    return None

 # TODO: base dependabot config on repo.get_languages() - ie {'Python': 22722, 'Shell': 328}

def validate_updates_for_langauges(
    repo: Repository,
    updates,
    error_object: DICTLIST,
    _: DICTLIST,
):
    """ ensures that for every known language/package ecosystem, there's a configured update task """
    languages = repo.get_languages()
    required_package_managers = []
    for language in languages:
        package_manager = find_language_in_ecosystem(language)
        if package_manager:
            logger.info("Language is in package manager: {}", package_manager)
            required_package_managers.append(package_manager)

    if required_package_managers:
        logger.debug(
            "Need to ensure updates exist for these package ecosystems: {}",
            ", ".join(required_package_managers),
            )
        package_managers_covered = []
        for update in updates:
            if "package-ecosystem" in update:
                if update["package-ecosystem"] in required_package_managers and update["package-ecosystem"] not in package_managers_covered:
                    package_managers_covered.append(update["package-ecosystem"])
                    logger.debug("Satisified requirement for {}", update["package-ecosystem"])
        if set(required_package_managers) != set(package_managers_covered):
            for manager in [ manager for manager in required_package_managers if manager not in package_managers_covered ]:
                add_result(error_object, CATEGORY, f"Package manager needs to be configured for {manager}")
        else:
            logger.debug("")

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
        elif update["package-ecosystem"] not in PACKAGE_ECOSYSTEM:
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

    # TODO: this only matters if there's languages that dependabot supports
    # if not dependabot_config:
    #     add_result(warnings_object, CATEGORY, "No dependabot configuration found.")
    #     return

    if "updates" in dependabot_config:
        validate_update_config(
            dependabot_config["updates"], errors_object, warnings_object
        )

        validate_updates_for_langauges(repo, dependabot_config["updates"], errors_object, warnings_object)
