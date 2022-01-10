""" checking for issues and PRs and things """

from loguru import logger
# from github.Repository import Repository
from .. import GithubLinter
from ..utils import DICTLIST, add_result, get_file_from_repo


CATEGORY = "testing"
LANGUAGES = ["all"]

def check_testing_yml_exists(
    github: GithubLinter,
    errors_object: DICTLIST,
    _: DICTLIST,
):
    """ Checks that .github/workflows/testing.yml exists """
    if github.current_repo:
        testingyml = get_file_from_repo(github.current_repo, ".github/workflows/testing.yml")

        if not testingyml:
            add_result(errors_object, CATEGORY, "File .github/workflows/testing.yml missing")
        logger.debug("Found .github/workflows/testing.yml")
