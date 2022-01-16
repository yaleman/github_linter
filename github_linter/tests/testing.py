""" checking for issues and PRs and things """

from typing import TypedDict

from loguru import logger

from .. import RepoLinter


CATEGORY = "testing"
LANGUAGES = ["all"]

class DefaultConfig(TypedDict):
    """ config object """

DEFAULT_CONFIG: DefaultConfig = {
}

def check_shellcheck(
    repo: RepoLinter
):
    """ If 'Shell' exists in repo languages, check for a shellcheck action """
    repo_langs = repo.repository.get_languages()

    if "Shell" not in repo_langs:
        return

    testfile = repo.cached_get_file(".github/workflows/testing.yml")
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

def check_testing_yml_exists(
    repo: RepoLinter
):
    """ Checks that .github/workflows/testing.yml exists """
    if not repo.repository.get_languages():
        repo.warning(CATEGORY, "No languages identified, didn't check for automated testing config")
        return

    testingyml = repo.cached_get_file(".github/workflows/testing.yml")

    if not testingyml:
        repo.error(CATEGORY, "File .github/workflows/testing.yml missing")
    logger.debug("Found .github/workflows/testing.yml")
