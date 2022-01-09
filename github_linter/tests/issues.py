""" checking for issues and PRs and things """

from loguru import logger

from .. import GithubLinter
from ..utils import DICTLIST, add_result


CATEGORY = "issues"
LANGUAGES = [
    "all"
]

# pylint: disable=unused-argument
def check_open_issues(
    github_object: GithubLinter,
    repo,
    _: DICTLIST,
    warnings_object: DICTLIST,  # warnings_object
) -> None:
    """ Adds a warning if there's open issues """
    if repo.open_issues:
        add_result(
            warnings_object,
            CATEGORY,
            f"There are {repo.open_issues} open issues for {repo.full_name}",
        )


# pylint: disable=unused-argument
def check_open_prs(
    github_object: GithubLinter,
    repo,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,  # warnings_object
) -> None:
    """ Adds a warning if there's open PRs """
    pulls = repo.get_pulls("open")
    if pulls.totalCount:
        logger.debug(
            "There's {} PRs... listing at least the latest 10.", pulls.totalCount
        )
        for pull in pulls.reversed[:10]:
            message = f"{repo.full_name} has an open PR: #{pull.number} - {pull.title} in {repo.full_name} (mergeable={pull.mergeable})"
            add_result(warnings_object, CATEGORY, message)
