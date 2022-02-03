""" checks for dependabot config """

from enum import Enum
import json
from typing import Any, Dict, List, TypedDict, Optional

from loguru import logger
import pydantic
import pytz
import ruamel.yaml # type: ignore

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
    config_filename : str
    schedule: Dict[str, str]


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


# pylint: disable=invalid-name
class IntervalEnum(str, Enum):
    """ possible intervals for dependabot """
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class DependabotSchedule(pydantic.BaseModel):
    """ schedule """
    interval: IntervalEnum
    day: Optional[str]
    time: Optional[str]
    timezone: Optional[str] # needs to be one of pytz.all_timezones

    # TODO: write tests for this
    @pydantic.validator("timezone")
    def validate_timezone(cls, value):
        """ validator """
        if value not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {value}")
        return value

    @pydantic.validator('day')
    def validate_day_value(cls, v, values):
        """ check you're specifying a valid day of the week """
        if values.get("day"):
            if 'interval' in values and values.get('day') not in [
                "monday"
                "tuesday"
                'wednesday'
                'thursday'
                "friday"
                "saturday"
                "sunday"
            ]:
                raise ValueError(f"Invalid day: {values['day']}")
        return v

class DependabotCommitMessage(pydantic.BaseModel):
    """ configuration model for the config
    https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#commit-message

    """
    prefix: Optional[str]
    prefix_development: Optional[str] = pydantic.Field(alias="prefix-development")
    include: Optional[str]

    @pydantic.validator("include")
    def validate_include(cls, value):
        """ checks for a valid entry """
        if value != "scope":
            raise ValueError("Only 'scope' can be specified in 'include' field.")



class DependabotUpdateConfig(pydantic.BaseModel):
    """ an update config """
    package_ecosystem: str = pydantic.Field(alias="package-ecosystem")
    directory: str = "/"

    schedule: DependabotSchedule
    allow: Optional[Dict[str,str]] # https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#allow
    assignees: Optional[List[str]]
    commit_message: Optional[DependabotCommitMessage] = pydantic.Field(alias="commit-message")
    ignore: Optional[List[str]]
    insecure_external_code_execution: Optional[str] = pydantic.Field(alias="insecure-external-code-execution")
    labels: Optional[List[str]]
    milestone: Optional[int]
    open_pull_requests_limit: Optional[int] = pydantic.Field(alias="open-pull-requests-limit")
    # TODO: this needs to be a thing - https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#pull-request-branch-nameseparator #pylint: disable=line-too-long
    # pull-request-branch-name.separator
    rebase_strategy: Optional[str] = pydantic.Field(alias="rebase-strategy")
    # TODO: registries typing for DependabotUpdateConfig
    registries: Optional[Any]
    reviewers: Optional[List[str]]
    target_branch: Optional[str] = pydantic.Field(alias="target-branch")
    vendor: Optional[bool]
    versioning_strategy: Optional[str] = pydantic.Field(alias="versioning-strategy")


    # TODO: write tests for this
    @pydantic.validator('package_ecosystem')
    def validate_package_ecosystem(cls, value):
        """ validates you're getting the right value """
        if value not in PACKAGE_ECOSYSTEM:
            raise ValueError(f"invalid value for package_ecosystem '{value}'")

    # TODO: write tests for this
    @pydantic.validator('rebase_strategy')
    def validate_rebase_strategy(cls, value):
        """ validates you're getting the right value """
        if value not in ["disabled", "auto"]:
            raise ValueError("rebase-strategy needs to be either 'auto' or 'disabled'.")

    # TODO: write tests for this
    @pydantic.validator('rebase_strategy')
    def validate_execution_permissions(cls, value):
        """ validates you're getting the right value """
        if value not in ["deny", "allow"]:
            raise ValueError("insecure-external-code-execution needs to be either 'allow' or 'deny'.")

DEFAULT_CONFIG: DefaultConfig = {
    "config_filename" : ".github/dependabot.yml",
    "schedule" : DependabotSchedule(
        interval="weekly",
        day="Monday",
        time="00:00",
        timezone= "Etc/UTC" # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    ).dict()
}

class DependabotConfigFile(pydantic.BaseModel):
    """ cnofiguration file"""
    version: int
    updates: Optional[List[DependabotUpdateConfig]]

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

def generate_expected_update_config(repo: RepoLinter) -> List[DependabotUpdateConfig]:
    """ generates the required configuration """

    updates: List[DependabotUpdateConfig] = []

    for language in repo.repository.get_languages():
        if find_language_in_ecosystem(language):
            logger.warning("Found lang/eco: {}, {}", language, find_language_in_ecosystem(language))

    return updates
# TODO: base dependabot config on repo.get_languages() - ie {'Python': 22722, 'Shell': 328}


def check_updates_for_languages(repo: RepoLinter):
    """ ensures that for every known language/package ecosystem, there's a configured update task """

    dependabot = load_file(repo)
    if not dependabot:
        return repo.error(CATEGORY, "Dependabot file not found")

    if not dependabot.updates:
        return repo.error(CATEGORY, "Updates config not found.")

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
    for update in dependabot.updates:
        if update.package_ecosystem:
            if (
                update.package_ecosystem in required_package_managers
                and update.package_ecosystem not in package_managers_covered
            ):
                package_managers_covered.append(update.package_ecosystem)
                logger.debug(
                    "Satisified requirement for {}", update.package_ecosystem
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
        # TODO: figure out what to do here
        return None
    return None


DEPENDABOT_SCHEDULE_INTERVALS = [
    "daily",
    "weekly",  # monday by default, or schedule.day if you want to change it
    "monthly",  # first of the month
]


def load_file(
    repo: RepoLinter,
) -> Optional[DependabotConfigFile]:
    """ grabs the dependabot config file and loads it """
    fileresult = repo.cached_get_file(repo.config[CATEGORY]["config_filename"])
    if not fileresult:
        logger.debug("Couldn't find dependabot config.")
        return None

    try:
        yaml_config = ruamel.yaml.YAML(pure=True).load(fileresult.decoded_content.decode("utf-8"))
        logger.debug(
            json.dumps(yaml_config, indent=4, default=str, ensure_ascii=False)
        )

        updates: List[DependabotUpdateConfig] = []
        if "updates" in yaml_config:
            for update in yaml_config["updates"]:
                updates.append(DependabotUpdateConfig(**update))
            yaml_config["updates"] = updates

        retval = DependabotConfigFile(**yaml_config)
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
        dependabot = load_file(repo)
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

def fix_create_dependabot_config(repo: RepoLinter):
    """ creates the dependabot config file """
    existing_config = load_file(repo)

    expected_config = generate_expected_update_config(repo)

    if not existing_config:
        # TODO: just write the full config
        logger.warning("Can't handle a missing dependabot config yet")
        return

    if existing_config and not existing_config.updates:
        existing_config.updates = expected_config

    else:
        # TODO: compare expected and existing config and update them.
        #for update in config["updates"]:
        #    update_parsed = DependabotUpdateConfig(**update)
        #    logger.debug(json.dumps(update_parsed.dict(exclude_unset=True, exclude_none=True), indent=4))
        logger.warning("Need to write the updatey bit!")
        return


def update_dependabot_config(old, new):
    """ bleep bloop, compares the two """
    # TODO: write update_dependabot_config
    raise NotImplementedError
