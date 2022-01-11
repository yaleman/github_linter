""" checks for dependabot config """

import json
from typing import Dict, List, Union, TypedDict, Optional

from loguru import logger
# from github.Repository import Repository
import pytz
import yaml

from github_linter import GithubLinter

# from . import GithubLinter
from ..exceptions import RepositoryNotSet
from ..types import DICTLIST
from ..utils import add_result

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
        "updates": List[Dict[str, Dict[str, str]]],
    },
)

PACKAGE_ECOSYSTEM: Dict[str, List[str]] = {
    "bundler": [],
    "cargo": ["rust"],
    "composer": [],
    "docker": [],
    "mix": [],
    "elm": [],
    "gitsubmodule": [],
    "github-actions": [],
    "gomod": [],
    "gradle": [],
    "maven": [],
    "npm": [],
    "nuget": [],
    "pip": ["python"],
    "terraform": ["HCL"],
}


def find_language_in_ecosystem(language: str) -> Optional[str]:
    """ checks to see if languages are in VALID_VALUES["package-ecosystem"] """
    for package in PACKAGE_ECOSYSTEM:
        lowerlang = [lang.lower() for lang in PACKAGE_ECOSYSTEM[package]]
        if language.lower() in lowerlang:
            return package
    return None


# TODO: base dependabot config on repo.get_languages() - ie {'Python': 22722, 'Shell': 328}

def check_updates_for_langauges(
    github_object: GithubLinter,
    error_object: DICTLIST,
    warnings_object: DICTLIST,
):
    """ ensures that for every known language/package ecosystem, there's a configured update task """

    if not github_object.current_repo:
        raise RepositoryNotSet


    dependabot = load_file(github_object, error_object, warnings_object)
    if not dependabot:
        return add_result(error_object, CATEGORY, "Dependabot file not found")

    if "updates" not in dependabot:
        return add_result(error_object, CATEGORY, "Updates config not found.")

    updates = dependabot["updates"]

    required_package_managers = []

    # get the languages from the repo
    languages = github_object.current_repo.get_languages()

    # compare them to the ecosystem languages
    for language in languages:
        package_manager = find_language_in_ecosystem(language)
        if package_manager:
            logger.debug("Language is in package manager: {}", package_manager)
            required_package_managers.append(package_manager)
    if not required_package_managers:
        logger.debug("No languages matched dependabot providers, stopping.")
        return None

    logger.debug(
        "Need to ensure updates exist for these package ecosystems: {}",
        ", ".join(required_package_managers),
    )
    package_managers_covered = []


    # check the update configs
    for update in updates:
        if "package-ecosystem" in update:
            if (
                update["package-ecosystem"] in required_package_managers
                and update["package-ecosystem"] not in package_managers_covered
            ):
                package_managers_covered.append(update["package-ecosystem"])
                logger.debug(
                    "Satisified requirement for {}", update["package-ecosystem"]
                )
    # check that the repo has full coverage
    if set(required_package_managers) != set(package_managers_covered):
        for manager in [
            manager
            for manager in required_package_managers
            if manager not in package_managers_covered
        ]:
            return add_result(
                error_object,
                CATEGORY,
                f"Package manager needs to be configured for {manager}",
            )
    else:
        # TODO: wot
        logger.debug(warnings_object)
        return None
    return None


DEPENDABOT_SCHEDULR_INTERVALS = [
    "daily",
    "weekly", # monday by default, or schedule.day if you want to change it
    "monthly", # first of the month
]

def load_file(
    github: GithubLinter,
    errors_object: DICTLIST,
    _: DICTLIST,
) -> Union[Dict, DEPENDABOT_CONFIG_FILE]:
    """ grabs the config file and loads it """
    fileresult = github.cached_get_file(".github/dependabot.yml")
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

def check_update_configs(
    github_object,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,  # warnings_object
):
    """ checks update config exists and is slightly valid """

    if not github_object.current_repo:
        raise RepositoryNotSet

    dependabot = load_file(github_object, errors_object, warnings_object)
    if not dependabot:
        logger.debug("Coudln't load dependabot config.")
        return

    if "updates" not in dependabot:
        add_result(
            errors_object,
            CATEGORY,
            "No udpates config in dependabot.yml."
        )
        return

    for update in dependabot["updates"]:
        logger.debug(json.dumps(update, indent=4))
        if "package-ecosystem" not in update:
            add_result(errors_object, CATEGORY, "package-ecosystem not set in an update")

        elif update["package-ecosystem"] not in PACKAGE_ECOSYSTEM:
            add_result(
                errors_object,
                CATEGORY,
                f"package-ecosystem set to invalid value: '{update['package-ecosystem']}'",
            )
        # checks there's a schedule and it has a valid timezone
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates
        if "schedule" not in update:
            add_result(
                errors_object,
                CATEGORY,
                f"Schedule missing from update {json.dumps(update)}"
            )
            return

        schedule: Dict[str, str] = update["schedule"]
        if "interval" not in schedule:
            add_result(
                errors_object,
                CATEGORY,
                f"Interval missing from schedule {json.dumps(schedule)}"
            )


        # not mandatory, but needs to be valid -
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone

        if "timezone" in schedule:
            timezone: str = schedule["timezone"]
            if timezone not in pytz.common_timezones:
                add_result(
                    errors_object,
                    CATEGORY,
                    f"Update timezone's not valid? {timezone}",
                )

def check_updates_have_directory_set(
    github_object: GithubLinter,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
    ):
    """ checks that each update config has 'directory' set """

    if not github_object.current_repo:
        raise RepositoryNotSet

    dependabot = load_file(github_object, errors_object, warnings_object)
    if not dependabot:
        logger.debug("Coudln't load dependabot config.")
        return

def check_dependabot_config(
    github_object: GithubLinter,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
):
    """ checks for dependabot config """

    if not github_object.current_repo:
        raise RepositoryNotSet

    dependabot_config = load_file(github_object, errors_object, warnings_object)

    if not dependabot_config:
        logger.debug("Didn't find a dependabot config.")
        return

    # if "updates" in dependabot_config and github_object.current_repo:
    #     validate_updates_for_langauges(
    #         github_object.current_repo, dependabot_config["updates"], errors_object, warnings_object
    #     )
