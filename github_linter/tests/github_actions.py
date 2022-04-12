""" github actions tests

the tests_per_language config has keys which are the Github-validated languages, eg Python or Dockerfile or Shell

templates for fixes are in templates/<language>/filename and match the language/filename from the config.

example config:

tests_per_language = {
    "Dockerfile" : ["build_container.yml"]
}

looks for .github/workflows/build_container.yml

templates/Dockerfile/build_container.yml would be used when running the fix

"""

from pathlib import Path
from typing import Dict, List, TypedDict

import json5 as json
from loguru import logger

from ..loaders import load_yaml_file
from ..repolinter import RepoLinter
from ..utils import get_fix_file_path

CATEGORY = "github_actions"

LANGUAGES = ["all"]


class DefaultConfig(TypedDict):
    """ config typing for module config """
    tests_per_language: Dict[str, List[str]]
    dependency_review: str

DEFAULT_CONFIG: DefaultConfig = {
    "tests_per_language" : {
        "Python" : [
            "mypy.yml",
            "pylint.yml",
            "pytest.yml",
        ],
        "Shell" : [
            "shellcheck.yml",
        ],
        "Dockerfile" : [
            "build_container.yml",
        ]
    },
    "dependency_review" : ".github/workflows/dependency_review.yml",
}

# https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone


def check_a_workflow_dir_exists(repo: RepoLinter) -> None:
    """ checks '.github/workflows/' exists """
    if not repo.cached_get_file(".github", clear_cache=True):
        repo.error(CATEGORY, ".github dir not found")
        return

    filename = ".github/workflows"
    result = repo.cached_get_file(filename, clear_cache=True)

    if not result:
        repo.error(CATEGORY, f"Workflows dir ({filename}) missing.")
        return


def check_language_workflows(repo: RepoLinter) -> None:
    """ Checks that the config files exist and then validates they have the **required** fields """

    for language in repo.repository.get_languages():
        logger.debug("Checking config for {} language files", language)

        if language in  repo.config[CATEGORY]["tests_per_language"]:
            logger.info("Found {}-related files", language)
            expected_files = repo.config[CATEGORY]["tests_per_language"][language]

            for filename in expected_files:
                filepath = f".github/workflows/{filename}"
                logger.warning("Checking for {}", filepath)
                config_file = load_yaml_file(repo, filepath)

                logger.debug(json.dumps(config_file, indent=4))
                if not config_file:
                    repo.error(
                        CATEGORY, f"Couldn't find/load github actions file: {filepath}"
                    )
                    continue

                for required_key in [
                    "name",
                    "on",
                    "jobs",
                ]:
                    if required_key not in config_file:
                        repo.error(CATEGORY, f"Missing key in action file {filepath}: {required_key}")


def fix_language_workflows(repo: RepoLinter) -> None:
    """ Creates the config files per-language """

    for language in repo.repository.get_languages():
        logger.debug("Checking config for {} language files", language)

        if language in  repo.config[CATEGORY]["tests_per_language"]:
            logger.info("Found {}-related files", language)
            expected_files = repo.config[CATEGORY]["tests_per_language"][language]

            for filename in expected_files:
                filepath = f".github/workflows/{filename}"
                logger.warning("Checking for {}", filepath)
                config_file = load_yaml_file(repo, filepath)

                logger.debug(json.dumps(config_file, indent=4))
                if not config_file:
                    # create the file
                    newfile = get_fix_file_path(CATEGORY, f"templates/{language}/{filename}")
                    if not newfile.exists():
                        raise ValueError(f"Can't find {newfile.resolve()} to create fix for {language}/{filename}")

                    commit_url = repo.create_or_update_file(
                        filepath=filepath,
                        newfile=newfile,
                        oldfile=None,
                        message=f'github_linter: Created {filepath} from fix_language_workflows'
                    )
                    repo.fix(CATEGORY, f"Created {filepath} from fix_language_workflows: {commit_url}")



def check_shellcheck(repo: RepoLinter) -> None:
    """ If 'Shell' exists in repo languages, check for a shellcheck action """
    repo_langs = repo.repository.get_languages()

    if "Shell" not in repo_langs:
        logger.debug("Github didn't find 'Shell' as a language, skipping this check'")
        return

    testfile = repo.cached_get_file(".github/workflows/shellcheck.yml")
    if not testfile:
        # covered by check_testing_yml_exists
        return
    if not testfile.decoded_content:
        # covered by check_testing_yml_exists
        return

    shellcheck_action: str = "ludeeus/action-shellcheck@master"
    if "testing" in repo.config:
        testing = repo.config["testing"]
        if "shellcheck_action" in testing:
            shellcheck_action = repo.config["testing"]["shellcheck_action"]
    if shellcheck_action not in testfile.decoded_content.decode("utf-8"):
        repo.error(
            CATEGORY,
            f"Shellcheck action string missing, expected {shellcheck_action}",
        )

class DependencyReviewFilePaths(TypedDict):
    """ typing """
    repo_file_path: str
    fix_file_path: Path

def get_dependency_review_file_paths(
    repo: RepoLinter,
    ) -> DependencyReviewFilePaths:
    """ gets the paths """
    retval = DependencyReviewFilePaths({
        "repo_file_path" : repo.config[CATEGORY]["dependency_review"],
        "fix_file_path" : get_fix_file_path(
        CATEGORY,
        "dependency_review.yml",
        ),
    })
    return retval

def check_dependency_review_file(repo: RepoLinter) -> None:
    """ checks for .github/workflows/dependency_review.yml

    and ensures it matches the template
    """
    repo.skip_on_archived()

    filepaths = get_dependency_review_file_paths(repo)
    existing_file = repo.cached_get_file(filepaths["repo_file_path"])
    fix_file_content = filepaths["fix_file_path"].read_bytes()

    if existing_file is None or existing_file.decoded_content != fix_file_content:
        repo.error(
            CATEGORY,
            f"Dependency review action is missing or needs update {filepaths['repo_file_path']}",
            )
        return
    logger.debug(f"Dependency review action is up to date {filepaths['repo_file_path']}")

def fix_dependency_review_file(repo: RepoLinter) -> None:
    """ checks for .github/workflows/dependency_review.yml

    and ensures it matches the template
    """
    repo.skip_on_archived()

    filepaths = get_dependency_review_file_paths(repo)
    existing_file = repo.cached_get_file(filepaths["repo_file_path"])
    fix_file_content = filepaths["fix_file_path"].read_bytes()

    if existing_file is not None and existing_file.decoded_content == fix_file_content:
        logger.debug(
            f"Dependency review action is up to date {filepaths['repo_file_path']}",
            )
        return
    result = repo.create_or_update_file(
        filepaths["repo_file_path"],
        newfile=fix_file_content,
        oldfile=existing_file,
        message="github_actions - update dependency_review workflow",
    )
    repo.fix(
        CATEGORY,
        f"Updated dependency_review workflow commit URL: {result}"
    )
