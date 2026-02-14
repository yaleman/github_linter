import pytest


from github_linter import GithubLinter
from github_linter.web import get_all_user_repos


@pytest.mark.network
def test_get_all_user_repos() -> None:
    """tests what we get back from it, can be slow and burn things"""
    linter = GithubLinter()
    linter.do_login()
    config = {
        "linter": {
            "owner_list": [
                "TerminalOutcomes",
            ]
        }
    }
    result = get_all_user_repos(linter, config)

    for repo in result:
        print(repo)
    print(f"Found {len(result)} repositories")
