"""github actions tests

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
from typing import Any, Dict, List, Optional, TypedDict

import json5 as json
from loguru import logger  # type: ignore
from pydantic import BaseModel, field_validator

from github_linter.fixes.github_actions import (
    get_repo_default_workflow_permissions,
    set_repo_default_workflow_permissions,
    VALID_DEFAULT_WORKFLOW_PERMISSIONS,
)

from ..loaders import load_yaml_file
from ..repolinter import RepoLinter
from ..utils import get_fix_file_path

CATEGORY = "github_actions"

LANGUAGES = ["all"]


class DefaultConfig(BaseModel):
    """config typing for module config"""

    tests_per_language: Dict[str, List[str]]
    # dev_packages: Dict[str, List[str]] # TODO: move this to pyproject.toml
    dependency_review: str
    default_workflow_permissions: str
    can_approve_pull_request_reviews: bool

    @field_validator("default_workflow_permissions")
    def validate_default_workflow_permissions(cls, value: str) -> str:
        """validate the default_workflow_permissions value"""
        if value not in VALID_DEFAULT_WORKFLOW_PERMISSIONS:
            raise ValueError(f"default_workflow_permissions must be one of {','.join(VALID_DEFAULT_WORKFLOW_PERMISSIONS)}")
        return value


DEFAULT_CONFIG = DefaultConfig.model_validate(
    {
        "tests_per_language": {
            "Python": [
                "mypy.yml",
                "pylint.yml",
                "pytest.yml",
            ],
            "Rust": [
                "rust_test.yml",
                "clippy.yml",
            ],
            "Shell": [
                "shellcheck.yml",
            ],
            "Dockerfile": [
                "build_container.yml",
            ],
        },
        # "dev_packages" : {
        #     "Python" : [
        #         "mypy",
        #         "ruff",
        #         "pytest",
        #         "black",
        # #     ]
        # },
        "dependency_review": ".github/workflows/dependency_review.yml",
        "default_workflow_permissions": "read",
        "can_approve_pull_request_reviews": True,
    }
)

# https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone


def check_a_workflow_dir_exists(repo: RepoLinter) -> None:
    """checks '.github/workflows/' exists"""
    if not repo.cached_get_file(".github", clear_cache=True):
        repo.error(CATEGORY, ".github dir not found")
        return

    filename = ".github/workflows"
    result = repo.cached_get_file(filename, clear_cache=True)

    if not result:
        repo.error(CATEGORY, f"Workflows dir ({filename}) missing.")
        return


def check_language_workflows(repo: RepoLinter) -> None:
    """Checks that the config files exist and then validates they have the **required** fields"""

    for language in repo.repository.get_languages():
        logger.debug("Checking config for {} language files", language)

        if language in repo.config[CATEGORY]["tests_per_language"]:
            logger.info("Found {}-related files", language)
            expected_files = repo.config[CATEGORY]["tests_per_language"][language]

            for filename in expected_files:
                filepath = f".github/workflows/{filename}"
                logger.debug("Checking for {}", filepath)
                config_file = load_yaml_file(repo, filepath)

                logger.debug(json.dumps(config_file, indent=4))
                if not config_file:
                    repo.error(CATEGORY, f"Couldn't find/load github actions file: {filepath}")
                    continue

                for required_key in [
                    "name",
                    "on",
                    "jobs",
                ]:
                    if required_key not in config_file:
                        repo.error(
                            CATEGORY,
                            f"Missing key in action file {filepath}: {required_key}",
                        )


def fix_language_workflows(repo: RepoLinter) -> None:
    """Creates the config files per-language"""

    for language in repo.repository.get_languages():
        logger.debug("Checking config for {} language files", language)

        if language in repo.config[CATEGORY]["tests_per_language"]:
            logger.info("Found {}-related files", language)
            expected_files = repo.config[CATEGORY]["tests_per_language"][language]

            for filename in expected_files:
                filepath = f".github/workflows/{filename}"
                logger.debug("Checking for {}", filepath)
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
                        message=f"github_linter: Created {filepath} from fix_language_workflows",
                    )
                    repo.fix(
                        CATEGORY,
                        f"Created {filepath} from fix_language_workflows: {commit_url}",
                    )


def check_shellcheck(repo: RepoLinter) -> None:
    """If 'Shell' exists in repo languages, check for a shellcheck action"""
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
    """typing"""

    repo_file_path: str
    fix_file_path: Path


def get_dependency_review_file_paths(
    repo: RepoLinter,
) -> DependencyReviewFilePaths:
    """gets the paths"""
    retval = DependencyReviewFilePaths(
        {
            "repo_file_path": repo.config[CATEGORY]["dependency_review"],
            "fix_file_path": get_fix_file_path(
                CATEGORY,
                "dependency_review.yml",
            ),
        }
    )
    return retval


def check_dependency_review_file(repo: RepoLinter) -> None:
    """checks for .github/workflows/dependency_review.yml

    and ensures it matches the template
    """
    repo.skip_on_private()
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


def nested_get(haystack: Dict[str, Any], needle: str) -> Optional[Any]:
    """digs into the haystack looking for the needle, layers are like "one.two.three.four" """
    if "." not in needle:
        return haystack.get(needle)
    split_needle = needle.split(".")
    first_layer_needle = split_needle[0]

    if first_layer_needle not in haystack:
        return None
    return nested_get(haystack[first_layer_needle], ".".join(split_needle[1:]))


def pylint_to_ruff_check_pyproject(repo: RepoLinter) -> None:
    """handles the pyproject.toml file if we're moving from pylint to ruff"""
    pyproject = repo.load_pyproject()
    if pyproject is None:
        return

    logger.debug("tool.poetry.dependencies: {}", pyproject.get("tool.poetry.dependencies"))

    stanzas = [
        "tool.poetry.dependencies",
        "tool.poetry.dev-dependencies",
        "tool.poetry.extras",
        "tool.poetry.group.dev.dependencies",
    ]
    for stanza in stanzas:
        dependencies = nested_get(pyproject, stanza)
        if dependencies is None:
            logger.debug("didn't find stanza {} in pyproject.toml", stanza)
            continue
        logger.debug("{}: {}", stanza, dependencies)
        if "pylint" in dependencies:
            repo.warning(
                CATEGORY,
                f"pylint found in pyproject dependency stanza: {stanza}, please migrate to ruff",
            )


def pylint_to_ruff_check_github_workflows(repo: RepoLinter) -> None:
    """checks for github actions with pylint mentioned in the run field of job steps"""

    filename = ".github/workflows/pylint.yml"

    workflow: Optional[Dict[str, Any]] = load_yaml_file(repo, filename)
    if workflow == {}:
        logger.debug("Couldn't find or load .github/workflows/pylint.yml")
        return
    if workflow is None:
        logger.debug("Couldn't find or load .github/workflows/pylint.yml")
        return

    if "jobs" not in workflow:
        logger.debug("No jobs in .github/workflows/pylint.yml")
        return

    jobs: Dict[str, Any] = workflow["jobs"]
    for job_name in jobs:
        logger.debug("job: {}", job_name)

        job = workflow["jobs"][job_name]

        if "steps" not in job:
            logger.debug("Couldn't find steps for job {}", job_name)
            continue
        steps: List[Dict[str, Any]] = job["steps"]

        for step_index, step in enumerate(steps):
            logger.info(step)
            step_name = step.get("name", f"step #{step_index}")
            if "run" not in step:
                logger.debug("No 'run' in step '{}', skipping!", step_name)
                continue
            if "pylint" in step["run"]:
                logger.debug("Found pylint in run: {}", step["run"])
                message = f'Github Action Workflow filename="{filename}" job="{job_name}" step="{step_name}" contains pylint in the run argument, please migrate to `ruff`.'
                repo.warning(CATEGORY, message)


def check_migrate_pylint_to_ruff(repo: RepoLinter) -> None:
    """checks if pylint's in the package list or run commands and suggests moving to ruff"""
    repo.skip_on_archived()
    repo.requires_language("Python")

    # Check for pyproject.toml and then look for the pylint package in there
    pyproject_file = repo.get_file("pyproject.toml")
    if pyproject_file is not None:
        pylint_to_ruff_check_pyproject(repo)

    # check for run commands which use pylint in the github action .github/workflows/pylint.yml
    pylint_to_ruff_check_github_workflows(repo)


def fix_dependency_review_file(repo: RepoLinter) -> None:
    """checks for .github/workflows/dependency_review.yml

    and ensures it matches the template
    """
    repo.skip_on_private()
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
    repo.fix(CATEGORY, f"Updated dependency_review workflow commit URL: {result}")


def fix_dependency_review_file_remove_private(repo: RepoLinter) -> None:
    """checks for .github/workflows/dependency_review.yml

    and ensures it doesn't exist in private repos
    """

    repo.skip_on_archived()
    repo.skip_on_public()

    filepaths = get_dependency_review_file_paths(repo)
    existing_file = repo.cached_get_file(filepaths["repo_file_path"])

    if existing_file is not None:
        commit_result = repo.repository.delete_file(
            path=filepaths["repo_file_path"],
            message="github_linter - removing dependency checker github action",
            sha=existing_file.sha,
        )
        if "commit" not in commit_result:
            result = "Unknown Commit URL"
        else:
            result = getattr(commit_result["commit"], "html_url", "")
        repo.fix(CATEGORY, f"Removed dependency_review workflow, commit URL: {result}")


def check_repo_workflow_permissions(repo: RepoLinter) -> bool:
    """check that the workflow permissions match expected settings"""
    repo.skip_on_archived()
    result = True
    api_response = get_repo_default_workflow_permissions(repo)
    if api_response.default_workflow_permissions != repo.config[CATEGORY]["default_workflow_permissions"]:
        repo.error(
            CATEGORY,
            f"default_workflow_permissions={api_response.default_workflow_permissions} expected {repo.config[CATEGORY]['default_workflow_permissions']}",
        )
        result = False
    if api_response.can_approve_pull_request_reviews != repo.config[CATEGORY]["can_approve_pull_request_reviews"]:
        repo.error(
            CATEGORY,
            f"can_approve_pull_request_reviews={api_response.can_approve_pull_request_reviews} expected {repo.config[CATEGORY]['can_approve_pull_request_reviews']}",
        )
        result = False
    return result


def fix_repo_workflow_permissions(repo: RepoLinter) -> None:
    """set the default workflow permissions"""
    repo.skip_on_archived()
    dwp = repo.config[CATEGORY]["default_workflow_permissions"]
    caprr = repo.config[CATEGORY]["can_approve_pull_request_reviews"]
    # TODO: make this only take action if the check doesn't pass
    if set_repo_default_workflow_permissions(
        repo,
        dwp,
        caprr,
    ):
        repo.fix(
            CATEGORY,
            f"Updated default workflow permissions to default_workflow_permissions={dwp} can_approve_pull_request_reviews={caprr}",
        )
