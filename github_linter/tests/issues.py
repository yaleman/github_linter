""" checking for issues and PRs and things """

from loguru import logger

from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..utils import DICTLIST, add_result


CATEGORY = "issues"
LANGUAGES = ["all"]

# pylint: disable=unused-argument
def check_open_issues(
    github_object: GithubLinter,
    _: DICTLIST,
    warnings_object: DICTLIST,  # warnings_object
) -> None:
    """ Adds a warning if there's open issues """
    if not github_object.current_repo:
        raise RepositoryNotSet
    if github_object.current_repo.open_issues:
        add_result(
            warnings_object,
            CATEGORY,
            f"There are {github_object.current_repo.open_issues} open issues for {github_object.current_repo.full_name}",
        )


# pylint: disable=unused-argument
def check_open_prs(
    github_object: GithubLinter,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,  # warnings_object
) -> None:
    """ Adds a warning if there's open PRs """
    if not github_object.current_repo:
        raise RepositoryNotSet

    pulls = github_object.current_repo.get_pulls("open")
    repo_full_name = github_object.current_repo.full_name
    if pulls.totalCount:
        logger.debug(
            "There's {} PRs... listing at least the latest 10.", pulls.totalCount
        )
        for pull in pulls.reversed[:10]:
            message = f"{repo_full_name} has an open PR: #{pull.number} - {pull.title} in {repo_full_name} (mergeable={pull.mergeable})"
            add_result(warnings_object, CATEGORY, message)
