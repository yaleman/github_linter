""" checking for issues and PRs and things """

from typing import TypedDict

from loguru import logger


from ..repolinter import RepoLinter
from ..utils import get_fix_file_path

CATEGORY = "issues"
LANGUAGES = ["all"]


class DefaultConfig(TypedDict):
    """ config typing for module config """

    stale_file: str


DEFAULT_CONFIG: DefaultConfig = {
    "stale_file": ".github/stale.yml",
}

# pylint: disable=unused-argument
def check_open_issues(
    repo: RepoLinter,
) -> None:
    """ Adds a warning if there's open issues """
    if repo.repository.open_issues:
        repo.warning(
            CATEGORY,
            f"There are {repo.repository.open_issues} open issues for {repo.repository.full_name} (https://github.com/{repo.repository.full_name}/issues)",
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


def check_stale_yml(
    repo: RepoLinter,
) -> None:
    """ checks that .github/stale.yml exists and has the right content """
    repo.skip_on_archived()

    filename = repo.config[CATEGORY]["stale_file"]

    filecontents = repo.cached_get_file(filename)

    if not filecontents:
        repo.error(CATEGORY, f"Missing {filename}")
        return
    return


def fix_stale_yml(
    repo: RepoLinter,
) -> None:
    """ fixes the .github/stale.yml file """
    repo.skip_on_archived()

    filename = repo.config[CATEGORY]["stale_file"]
    filecontents = repo.cached_get_file(filename)

    fix_file = get_fix_file_path(CATEGORY, "stale.yml")

    if filecontents is None or (filecontents.decoded_content != fix_file.read_bytes()):
        result = repo.create_or_update_file(
            filename,
            fix_file,
            filecontents,
            "github_linter.issues updating .github/stale.yml",
        )
        if result:
            repo.fix(CATEGORY, f"Updated {fix_file.name} - commit URL: {result}")
