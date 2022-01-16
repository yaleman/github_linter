""" checking for issues and PRs and things """

from typing import TypedDict

from loguru import logger

from .. import RepoLinter

CATEGORY = "issues"
LANGUAGES = ["all"]


class DefaultConfig(TypedDict):
    """ config typing for module config """

DEFAULT_CONFIG: DefaultConfig = {
}

# pylint: disable=unused-argument
def check_open_issues(
    repo: RepoLinter,
) -> None:
    """ Adds a warning if there's open issues """
    if repo.repository.open_issues:
        repo.warning(CATEGORY,
            f"There are {repo.repository.open_issues} open issues for {repo.repository.full_name}",
        )


# pylint: disable=unused-argument
def check_open_prs(
    repo: RepoLinter,
) -> None:
    """ Adds a warning if there's open PRs """

    pulls = repo.repository.get_pulls("open")
    repo_full_name = repo.repository.full_name
    if pulls.totalCount:
        logger.debug(
            "There's {} PRs... listing at least the latest 10.", pulls.totalCount
        )
        for pull in pulls.reversed[:10]:
            message = f"{repo_full_name} has an open PR: #{pull.number} - {pull.title} in {repo_full_name} (mergeable={pull.mergeable})"
            repo.warning(CATEGORY, message)
