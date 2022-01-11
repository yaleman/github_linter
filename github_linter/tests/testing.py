""" checking for issues and PRs and things """

from loguru import logger
# from github.Repository import Repository
from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..utils import DICTLIST, add_result


CATEGORY = "testing"
LANGUAGES = ["all"]

def check_shellcheck(
    github: GithubLinter,
    errors_object: DICTLIST,
    _: DICTLIST,
):
    """ If 'Shell' exists in repo languages, check for a shellcheck action """
    if not github.current_repo:
        raise RepositoryNotSet

    repo_langs = github.current_repo.get_languages()

    if "Shell" not in repo_langs:
        return

    testfile = github.cached_get_file(".github/workflows/testing.yml")
    if not testfile:
        # covered by check_testing_yml_exists
        return
    if not testfile.decoded_content:
        # covered by check_testing_yml_exists
        return

    shellcheck_action = "ludeeus/action-shellcheck@master"
    if "testing" in github.config and "shellcheck_action" in github.config["testing"]:
        shellcheck_action = github.config["testing"]["shellcheck_action"]

    if shellcheck_action not in testfile.decoded_content.decode("utf-8"):
        add_result(
            errors_object,
            CATEGORY,
            f"Shellcheck action string missing, expected {shellcheck_action}",
            )

def check_testing_yml_exists(
    github: GithubLinter,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
):
    """ Checks that .github/workflows/testing.yml exists """
    if not github.current_repo:
        raise RepositoryNotSet

    if not github.current_repo.get_languages():
        add_result(warnings_object, CATEGORY, "No languages identified, didn't check for automated testing config")
        return

    testingyml = github.cached_get_file(".github/workflows/testing.yml")

    if not testingyml:
        add_result(errors_object, CATEGORY, "File .github/workflows/testing.yml missing")
    logger.debug("Found .github/workflows/testing.yml")
