""" checks for dependabot config """

import json
from typing import Dict, List, Union, TypedDict, Optional

from loguru import logger

# from github.Repository import Repository
import pytz

# TODO: replace this with ruamel.yaml so we only have one cursed dependency
import yaml

from github_linter import RepoLinter

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


class DefaultConfig(TypedDict):
    """ config typing for module config """


DEFAULT_CONFIG: DefaultConfig = {}

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


def check_updates_for_languages(repo: RepoLinter):
    """ ensures that for every known language/package ecosystem, there's a configured update task """

    dependabot = load_file(repo)
    if not dependabot:
        return repo.error(CATEGORY, "Dependabot file not found")

    if "updates" not in dependabot:
        return repo.error(CATEGORY, "Updates config not found.")

    updates = dependabot["updates"]

    required_package_managers = []

    # get the languages from the repo
    languages = repo.repository.get_languages()

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
            repo.error(
                CATEGORY,
                f"Package manager needs to be configured for {manager}",
            )
    else:
        # TODO: wot
        return None
    return None


DEPENDABOT_SCHEDULR_INTERVALS = [
    "daily",
    "weekly",  # monday by default, or schedule.day if you want to change it
    "monthly",  # first of the month
]


def load_file(
    repo: RepoLinter,
) -> Union[Dict, DEPENDABOT_CONFIG_FILE]:
    """ grabs the dependabot config file and loads it """
    fileresult = repo.cached_get_file(".github/dependabot.yml")
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
        repo.error(CATEGORY, f"Failed to parse dependabot config: {exc}")
    return {}


def check_update_configs(
    repo: RepoLinter,
):
    """ checks update config exists and is slightly valid """

    dependabot = load_file(repo)
    if not dependabot:
        logger.debug("Coudln't load dependabot config.")
        return

    if "updates" not in dependabot:
        repo.error(CATEGORY, "No udpates config in dependabot.yml.")
        return

    for update in dependabot["updates"]:
        logger.debug(json.dumps(update, indent=4))
        if "package-ecosystem" not in update:
            repo.error(CATEGORY, "package-ecosystem not set in an update")

        elif update["package-ecosystem"] not in PACKAGE_ECOSYSTEM:
            repo.error(
                CATEGORY,
                f"package-ecosystem set to invalid value: '{update['package-ecosystem']}'",
            )
        # checks there's a schedule and it has a valid timezone
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates
        if "schedule" not in update:
            repo.error(CATEGORY, f"Schedule missing from update {json.dumps(update)}")
            return

        schedule: Dict[str, str] = update["schedule"]
        if "interval" not in schedule:
            repo.error(
                CATEGORY, f"Interval missing from schedule {json.dumps(schedule)}"
            )

        # not mandatory, but needs to be valid -
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone

        if "timezone" in schedule:
            timezone: str = schedule["timezone"]
            if timezone not in pytz.common_timezones:
                repo.error(
                    CATEGORY,
                    f"Update timezone's not valid? {timezone}",
                )


def check_updates_have_directory_set(
    repo: RepoLinter,
):
    """ checks that each update config has 'directory' set """

    dependabot = load_file(repo)
    if not dependabot:
        logger.debug("Coudln't load dependabot config.")
        return


def check_dependabot_config(
    repo: RepoLinter,
):
    """ checks for dependabot config """

    dependabot_config = load_file(repo)

    if not dependabot_config:
        logger.debug("Didn't find a dependabot config.")
        return

    # if "updates" in dependabot_config and repo.repository:
    #     validate_updates_for_langauges(
    #         repo.repository, dependabot_config["updates"], errors_object, warnings_object
    #     )


def check_dependabot_vulnerability_enabled(
    repo: RepoLinter,
):
    """ checks for dependabot config """
    if not repo.repository.get_vulnerability_alert():
        repo.error(CATEGORY, "Vulnerability reports on repository are not enabled.")


def fix_enable_vulnerability_alert(repo: RepoLinter):
    """ enables vulnerability alerts on a repository """
    if repo.repository.enable_vulnerability_alert():
        repo.fix(CATEGORY, "Enabled vulnerability reports on repository.")
    else:
        repo.error(CATEGORY, "Failed to enable vulnerability reports on repository.")


def fix_enable_automated_security_fixes(repo: RepoLinter):
    """ enables dependabot on a repository """
    if repo.repository.enable_automated_security_fixes():
        repo.fix(CATEGORY, "Enabled automated security fixes on repository.")
    else:
        repo.error(CATEGORY, "Failed to enable automated security fixes.")
