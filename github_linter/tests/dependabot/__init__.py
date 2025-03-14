"""checks for dependabot config"""

from io import StringIO
import json
import sys
from typing import List

from github.GithubException import GithubException, UnknownObjectException
from loguru import logger
import pydantic
from requests import JSONDecodeError
from ruyaml import YAML
from ruyaml.scalarstring import DoubleQuotedScalarString

from github_linter.repolinter import RepoLinter
from github_linter.utils import get_fix_file_path
from .types import (
    DefaultConfig,
    DependabotConfigFile,
    DependabotSchedule,
    DependabotUpdateConfig,
)

from .utils import find_language_in_ecosystem, load_dependabot_config_file

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


DEFAULT_CONFIG: DefaultConfig = DefaultConfig(
    **{
        "config_filename": ".github/dependabot.yml",
        "schedule": DependabotSchedule.model_validate(
            {
                "interval": "weekly",
                "day": "monday",
                "time": DoubleQuotedScalarString("00:00"),
                "timezone": "Etc/UTC",  # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
            }
        ).model_dump(),
        # TODO: merge this under the packages
        # "groups": {
        #     "production-dependencies": {"dependency-type": "production"},
        #     "development-dependencies": {"dependency-type": "development"},
        # },
        "allow_auto_merge": False,
    }
)


def generate_expected_update_config(
    repo: RepoLinter,
) -> DependabotConfigFile:
    """generates the required configuration"""

    updates: List[DependabotUpdateConfig] = []
    for language in repo.repository.get_languages():
        if find_language_in_ecosystem(language):
            logger.debug(
                "Found lang/eco: {}, {}", language, find_language_in_ecosystem(language)
            )
            new_config = DependabotUpdateConfig.model_validate(
                {
                    "package-ecosystem": find_language_in_ecosystem(language),
                    "schedule": repo.config[CATEGORY]["schedule"],
                    "directory": "/",
                },
            )
            updates.append(new_config)
    github_actions_exists = False
    for update in updates:
        if update.package_ecosystem == "github-actions":
            github_actions_exists = True
    if not github_actions_exists:
        updates.append(
            DependabotUpdateConfig.model_validate(
                {
                    "package-ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": repo.config[CATEGORY]["schedule"],
                }
            )
        )
    config_file = DependabotConfigFile(
        version=2,
        updates=updates,
    )
    logger.debug("Dumping expected_update_config")
    logger.debug(json.dumps(config_file.model_dump(), indent=4, default=str))
    return config_file


# pylint: disable=too-many-branches
def check_updates_for_languages(repo: RepoLinter) -> None:
    """ensures that for every known language/package ecosystem, there's a configured update task"""

    repo.skip_on_archived()
    dependabot = load_dependabot_config_file(repo, CATEGORY)
    if dependabot is None or not dependabot:
        repo.error(CATEGORY, "Dependabot file not found")
        return

    if not dependabot.updates:
        repo.error(CATEGORY, "Updates config not found.")
        return

    required_package_managers = [
        "github-actions",  # included by default because ... y'know.
    ]

    # get the languages from the repo
    languages = repo.repository.get_languages()
    logger.debug("Found the following languages: {}", ",".join(languages))

    # compare them to the ecosystem languages
    for language in languages:
        package_manager = find_language_in_ecosystem(language)
        if package_manager:
            logger.debug("Language is in package manager: {}", package_manager)
            required_package_managers.append(package_manager)

    try:
        get_workflows = repo.repository.get_dir_contents(".github/workflows")
        if get_workflows:
            logger.debug("List of files in .github/workflows: {}", get_workflows)
            for file_details in get_workflows:
                if file_details.path.endswith(".yml"):
                    required_package_managers.append("github-actions")
                    logger.debug("Adding github-actions to required checks..")
                    break
    except TypeError:
        logger.debug("Couldn't get contents of dir '.github/workflows', skipping.")
    except UnknownObjectException:
        logger.debug("Couldn't get contents of dir '.github/workflows', skipping.")

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
                logger.debug("Satisified requirement for {}", update.package_ecosystem)
            else:
                logger.debug(
                    "Found {} already in package_managers_covered",
                    update.package_ecosystem,
                )
        else:
            logger.warning(
                "Found unexpected package-ecosystem setting: '{}', not in {}",
                update.package_ecosystem,
                ",".join(required_package_managers),
            )
            logger.debug(update.model_dump())

    # check that the repo has full coverage
    if set(required_package_managers) != set(package_managers_covered):
        missing_package_managers = [
            manager
            for manager in required_package_managers
            if manager not in package_managers_covered
        ]
        for manager in missing_package_managers:
            repo.error(
                CATEGORY,
                f"Package manager needs to be configured for {manager}",
            )

        extra_package_managers = [
            manager
            for manager in package_managers_covered
            if manager not in required_package_managers
        ]

        for extra_manager in extra_package_managers:
            repo.error(
                CATEGORY,
                f"Package manager {extra_manager} is configured but not needed",
            )


def check_dependabot_config_valid(
    repo: RepoLinter,
) -> None:
    """checks update config exists and is slightly valid"""

    repo.skip_on_archived()
    try:
        dependabot = load_dependabot_config_file(repo, CATEGORY)
    except pydantic.ValidationError as validation_error:
        repo.error(CATEGORY, f"Failed to parse dependabot config: {validation_error}")
        return None

    if not dependabot:
        logger.debug("Couldn't load dependabot config.")
        return None

    if not dependabot.updates:
        repo.error(CATEGORY, "No updates config in dependabot.yml.")
        return None

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
        # if "interval" not in schedule.model_dump():
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
    return None


def check_updates_have_directory_set(
    repo: RepoLinter,
) -> None:
    """checks that each update config has 'directory' set"""

    repo.skip_on_archived()

    # TODO: finish check_updates_have_directory_set
    dependabot = load_dependabot_config_file(repo, CATEGORY)
    if not dependabot:
        repo.error(CATEGORY, "Couldn't load dependabot config.")


def check_dependabot_config(
    repo: RepoLinter,
) -> None:
    """checks for dependabot config"""

    repo.skip_on_archived()
    # TODO: finish check_dependabot_config
    dependabot_config = load_dependabot_config_file(repo, CATEGORY)

    if not dependabot_config:
        repo.error(CATEGORY, "Didn't find a dependabot config.")


def check_dependabot_vulnerability_enabled(
    repo: RepoLinter,
) -> None:
    """checks for dependabot vulnerability alert config"""
    repo.skip_on_archived()
    if not repo.repository.get_vulnerability_alert():
        repo.error(CATEGORY, "Vulnerability reports on repository are not enabled.")


def check_dependabot_automerge_workflow(repo: RepoLinter) -> None:
    """checks the repo config file and see if auto-merge is enabled"""
    # TODO: the github module doesn't support directly querying the settings for this?
    repo.skip_on_archived()
    filepath = ".github/workflows/dependabot_auto_merge.yml"
    fileresult = repo.get_file(filepath)
    if fileresult is None or fileresult.decoded_content.decode("utf-8").strip() == "":
        return repo.error(CATEGORY, f"{filepath} missing")
    if (
        fileresult.decoded_content.decode("utf-8")
        != get_fix_file_path(category=CATEGORY, filename=filepath).read_text()
    ):
        repo.warning(CATEGORY, f"Content differs for {filepath}")
        # show the diff between the two files
        # repo.diff_file(
        #     fileresult.decoded_content.decode("utf-8"),
        #     get_fix_file_path(category=CATEGORY, filename=filepath).read_text(),
        # )

    # def check_dependabot_grouped_security_updates(repo: RepoLinter) -> None:
    """Checks that grouped_security updates are configured in Dependabot"""
    # TODO: can't find the REST endpoint for this :(
    # repo.skip_on_archived()
    # url = f"https://github.com/{repo.repository3.full_name}/settings/update_security_products_settings"
    # payload = {"_method": "put", "vulnerability_updates_grouping_enabled": 1}
    # logger.info(f"{url=}")
    # logger.info(f"{payload=}")


def fix_dependabot_automerge_workflow(repo: RepoLinter) -> None:
    """adds the automerge config"""
    repo.skip_on_archived()
    repo.skip_on_protected()

    filepath = ".github/workflows/dependabot_auto_merge.yml"
    fileresult = repo.get_file(filepath)
    if fileresult is None:
        result = repo.create_or_update_file(
            filepath=filepath,
            newfile=get_fix_file_path(category=CATEGORY, filename=filepath),
            oldfile=fileresult,
            message=f"Created {filepath}",
        )
        return repo.fix(CATEGORY, f"Created {filepath}, commit url: {result}")
    if (
        fileresult.decoded_content.decode("utf-8")
        != get_fix_file_path(category=CATEGORY, filename=filepath).read_text()
    ):
        result = repo.create_or_update_file(
            filepath=filepath,
            newfile=get_fix_file_path(category=CATEGORY, filename=filepath),
            oldfile=fileresult,
            message=f"Updated {filepath} to latest version",
        )
        return repo.fix(
            CATEGORY, f"Updated {filepath} to latest version, commit url: {result}"
        )
    logger.debug("{} already exists and has the right contents!", filepath)
    return None


def fix_dependabot_vulnerability_enabled(repo: RepoLinter) -> None:
    """enables vulnerability alerts on a repository"""
    repo.skip_on_archived()
    if repo.repository.enable_vulnerability_alert():
        repo.fix(CATEGORY, "Enabled vulnerability reports on repository.")
    else:
        repo.error(CATEGORY, "Failed to enable vulnerability reports on repository.")


def fix_enable_automated_security_fixes(repo: RepoLinter) -> None:
    """enables dependabot on a repository, there doesn't seem to be a way to *check* this?"""
    repo.skip_on_archived()
    if repo.repository.enable_automated_security_fixes():
        repo.fix(CATEGORY, "Enabled automated security fixes on repository.")
    else:
        repo.error(CATEGORY, "Failed to enable automated security fixes.")


def fix_create_dependabot_config(repo: RepoLinter) -> None:
    """creates the dependabot config file"""

    repo.skip_on_archived()

    expected_config = generate_expected_update_config(repo)

    updates = [
        val.dict(by_alias=True, exclude_unset=True, exclude_none=True)
        for val in expected_config.updates
    ]
    update_dict = {
        "version": expected_config.version,
        "updates": updates,
    }

    logger.debug(json.dumps(update_dict, indent=4))
    yaml = YAML()
    yaml.preserve_quotes = False  # type: ignore
    # yaml.default_flow_style = None
    buf = StringIO()
    yaml.dump(data=update_dict, stream=buf)
    buf.seek(0)
    newfilecontents = buf.read()
    logger.debug("New contents: \n{}", newfilecontents)
    # raise NotImplementedError
    if newfilecontents != repo.cached_get_file(
        repo.config[CATEGORY]["config_filename"], True
    ):
        logger.debug("Updating file")
        try:
            result = repo.create_or_update_file(
                filepath=repo.config[CATEGORY]["config_filename"],
                newfile=newfilecontents,
                oldfile=repo.cached_get_file(repo.config[CATEGORY]["config_filename"]),
                message=f"github_linter - {CATEGORY} - updating config",
            )
            if result is not None:
                repo.fix(
                    CATEGORY,
                    f"Updated {repo.config[CATEGORY]['config_filename']} - {result}",
                )
            else:
                logger.debug("No changes to {}, file content matched.")
        except GithubException as ghe:
            logger.error(
                "Failed to update file, bailing now! repo={}, filename={} error={}",
                repo.repository.full_name,
                repo.config[CATEGORY]["config_filename"],
                ghe,
            )
            sys.exit(1)


def check_repository_automerge(repo: RepoLinter) -> None:
    """checks that a repository has auto-merge enabled"""

    # API docs: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#update-a-repository

    # GitHub support - update this setting from the Update a repository endpoint. pass that configuration using the `allow_auto_merge` parameter on the body of that request.
    repo.skip_on_archived()

    expected_result = repo.config.get(CATEGORY, {}).get("allow_auto_merge", False)
    res = repo.repository3._get(url=repo.repository3.url)
    try:
        configured = res.json().get("allow_auto_merge")
    except JSONDecodeError as error:
        repo.error(
            CATEGORY, f"Failed to decode JSON while checking allow_auto_merge: {error}"
        )
        return None
    if configured is None:
        repo.error(CATEGORY, "None result in allow_auto_merge")
    if configured == expected_result:
        logger.debug(
            "allow_auto_merge matches expected setting, is set to  {}", configured
        )
    else:
        repo.error(
            CATEGORY,
            f"allow_auto_merge is set to {configured}, expected {expected_result}",
        )


def fix_repository_automerge(repo: RepoLinter) -> None:
    """ensures that a repository has auto-merge enabled"""

    # API docs: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#update-a-repository

    # GitHub support - update this setting from the Update a repository endpoint. pass that configuration using the `allow_auto_merge` parameter on the body of that request.

    repo.skip_on_archived()

    auto_merge_setting = repo.config.get(CATEGORY, {}).get("allow_auto_merge", False)

    logger.debug("Setting auto_merge_setting to {}", auto_merge_setting)
    request_body = {
        "allow_auto_merge": auto_merge_setting,
    }
    # url = f"/repos/{repo.repository.full_name}"
    res = repo.repository3._patch(url=repo.repository3.url, json=request_body)
    logger.debug(res.json())
    if (
        res.status_code == 200
        and res.json().get("allow_auto_merge") == auto_merge_setting
    ):
        repo.fix(
            CATEGORY, f"Updated repository auto-merge setting to {auto_merge_setting}"
        )
    else:
        repo.error(
            CATEGORY,
            f"Failed to update repository auto-merge setting to {auto_merge_setting} status code: {res.status_code} response['allow_auto_merge']: {res.json().get('allow_auto_merge')}",
        )
