""" checks for dependabot config """

# from enum import Enum
from io import StringIO
import json
from typing import Any, Dict, List, TypedDict, Optional

from loguru import logger
import pydantic
from ruyaml import YAML # type: ignore

from github_linter.repolinter import RepoLinter

from .types import (
    DefaultConfig,
    DependabotConfigFile,
    DependabotSchedule,
    DependabotUpdateConfig,
)
from .constants import PACKAGE_ECOSYSTEM

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



DEFAULT_CONFIG: DefaultConfig = {
    "config_filename" : ".github/dependabot.yml",
    "schedule" : DependabotSchedule(
        interval="weekly",
        day="monday",
        time="00:00",
        timezone= "Etc/UTC" # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    ).dict()
}



def find_language_in_ecosystem(language: str) -> Optional[str]:
    """ checks to see if languages are in VALID_VALUES["package-ecosystem"] """
    for package in PACKAGE_ECOSYSTEM:
        lowerlang = [lang.lower() for lang in PACKAGE_ECOSYSTEM[package]]
        if language.lower() in lowerlang:
            return package
    return None

def generate_expected_update_config(
    repo: RepoLinter,
    ) -> DependabotConfigFile:
    """ generates the required configuration """


    updates: List[DependabotUpdateConfig] = []
    for language in repo.repository.get_languages():
        if find_language_in_ecosystem(language):
            logger.warning("Found lang/eco: {}, {}", language, find_language_in_ecosystem(language))
            new_config = DependabotUpdateConfig.construct(
                package_ecosystem=find_language_in_ecosystem(language),
                schedule=repo.config[CATEGORY]["schedule"],
            )
            updates.append(new_config)
    config_file = DependabotConfigFile(
        version=2,
        updates=updates,
    )
    return config_file
# TODO: base dependabot config on repo.get_languages() - ie {'Python': 22722, 'Shell': 328}


def check_updates_for_languages(repo: RepoLinter) -> None:
    """ ensures that for every known language/package ecosystem, there's a configured update task """

    dependabot = load_dependabot_config_file(repo)
    if dependabot is None or not dependabot:
        repo.error(CATEGORY, "Dependabot file not found")
        return

    if not dependabot.updates:
        repo.error(CATEGORY, "Updates config not found.")
        return

    required_package_managers = []

    # get the languages from the repo
    languages = repo.repository.get_languages()
    logger.debug("Found the following languages: {}", ','.join(languages))

    # compare them to the ecosystem languages
    for language in languages:
        package_manager = find_language_in_ecosystem(language)
        if package_manager:
            logger.debug("Language is in package manager: {}", package_manager)
            required_package_managers.append(package_manager)
    if not required_package_managers:
        logger.debug("No languages matched dependabot providers, stopping.")
        return

    logger.debug(
        "Need to ensure updates exist for these package ecosystems: {}",
        ", ".join(required_package_managers),
    )

    package_managers_covered = []

    # check the update configs
    for update in dependabot.updates:
        if update.package_ecosystem in required_package_managers:
            if update.package_ecosystem not in package_managers_covered:
                package_managers_covered.append(update.package_ecosystem)
                logger.debug(
                    "Satisified requirement for {}", update.package_ecosystem
                )
            else:
                logger.debug("Found {} already in package_managers_covered", update.package_ecosystem)
        else:
            logger.warning(
                "Found unexpected package-ecosystem setting: '{}', not in {}",
                update.package_ecosystem,
                ','.join(required_package_managers),
                )
            logger.debug(update.dict())
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
        # TODO: figure out what to do here
        return
    return


DEPENDABOT_SCHEDULE_INTERVALS = [
    "daily",
    "weekly",  # monday by default, or schedule.day if you want to change it
    "monthly",  # first of the month
]


def load_dependabot_config_file(
    repo: RepoLinter,
) -> Optional[DependabotConfigFile]:
    """ grabs the dependabot config file and loads it """
    fileresult = repo.cached_get_file(repo.config[CATEGORY]["config_filename"])
    if not fileresult:
        logger.debug("Couldn't find dependabot config.")
        return None

    try:
        logger.debug("Parsing loaded file into YAML")
        yaml_config = YAML(pure=True).load(fileresult.decoded_content.decode("utf-8"))
        logger.debug("Dumping YAML-> dict file")
        logger.debug(
            json.dumps(yaml_config, indent=4, default=str, ensure_ascii=False)
        )

        # updates: List[DependabotUpdateConfig] = []
        # if "updates" in yaml_config:
        #     for update in yaml_config["updates"]:
        #         updates.append(DependabotUpdateConfig(**update))
        #     yaml_config["updates"] = updates

        retval = DependabotConfigFile.parse_obj(yaml_config)
        logger.debug("dumping DependabotConfigFile")
        logger.debug(json.dumps(retval.dict(), indent=4, default=str))
        for update in retval.updates:
            logger.debug("Package: {}", update.package_ecosystem)
        return retval
    except Exception as exc: #pylint: disable=broad-except
        logger.error("Failed to parse dependabot config: {}", exc)
        repo.error(CATEGORY, f"Failed to parse dependabot config: {exc}")
    return None


def check_update_configs(
    repo: RepoLinter,
):
    """ checks update config exists and is slightly valid """

    try:
        dependabot = load_dependabot_config_file(repo)
    except pydantic.ValidationError as validation_error:
        repo.error(CATEGORY, f"Failed to parse dependabot config: {validation_error}")
        return

    if not dependabot:
        logger.debug("Couldn't load dependabot config.")
        return

    if not dependabot.updates:
        repo.error(CATEGORY, "No updates config in dependabot.yml.")
        return

    for update in dependabot.updates:
        logger.debug(json.dumps(update.json(), indent=4))
        # if "package-ecosystem" not in update:
            # repo.error(CATEGORY, "package-ecosystem not set in an update")

        # checks there's a schedule and it has a valid timezone
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates
        # if not update."schedule" not in update:
            # repo.error(CATEGORY, f"Schedule missing from update {json.dumps(update)}")
            # return

        # schedule: DependabotSchedule = update.schedule
        # if "interval" not in schedule.dict():
        #     repo.error(
        #         CATEGORY, f"Interval missing from schedule {json.dumps(schedule)}"
        #     )

        # not mandatory, but needs to be valid -
        # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone

        # if "timezone" in schedule:
        #     timezone: str = schedule["timezone"]
        #     if timezone not in pytz.common_timezones:
        #         repo.error(
        #             CATEGORY,
        #             f"Update timezone's not valid? {timezone}",
        #         )


def check_updates_have_directory_set(
    repo: RepoLinter,
):
    """ checks that each update config has 'directory' set """

    dependabot = load_dependabot_config_file(repo)
    if not dependabot:
        logger.debug("Coudln't load dependabot config.")
        return


def check_dependabot_config(
    repo: RepoLinter,
):
    """ checks for dependabot config """

    dependabot_config = load_dependabot_config_file(repo)

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

def fix_create_dependabot_config(repo: RepoLinter):
    """ creates the dependabot config file """
    existing_config = load_dependabot_config_file(repo)

    expected_config = generate_expected_update_config(repo)

    #if not existing_config:
    #    # TODO: just write the full config
    #    logger.warning("Can't handle a missing dependabot config yet")
    #    return

    updates = [ val.dict(by_alias=True, exclude_unset=True, exclude_none=True) for val in expected_config.updates ]
    update_dict = {
        "version" : expected_config.version,
        "updates" : updates,
    }

    if existing_config is not None and update_dict == existing_config.dict(by_alias=True, exclude_unset=True, exclude_none=True):
        logger.debug("Don't need to update config ... ")
        return None
    yaml = YAML()
    yaml.preserve_quotes = True # type: ignore
    buf = StringIO()
    yaml.dump(
        data=update_dict,
        stream=buf
        )
    buf.seek(0)
    newfilecontents = buf.read()
    logger.debug("New contents: \n{}", newfilecontents)

    if newfilecontents != repo.cached_get_file(repo.config[CATEGORY]["config_filename"]):
        result = repo.create_or_update_file(
            filepath=repo.config[CATEGORY]["config_filename"],
            newfile=newfilecontents,
            oldfile=repo.cached_get_file(repo.config[CATEGORY]["config_filename"]),
            message=f"github_linter - {CATEGORY} - updating config"
        )
        if result is not None:
            repo.fix(CATEGORY, f"Updated {repo.config[CATEGORY]['config_filename']} - {result}")
        else:
            logger.debug("No changes to {}, file content matched.")
    return None


def update_dependabot_config(old, new):
    """ bleep bloop, compares the two """
    # TODO: write update_dependabot_config
    raise NotImplementedError
