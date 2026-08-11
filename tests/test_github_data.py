import pytest

from github_linter import GithubLinter
from github_linter.web import get_all_user_repos


class StubRepo:
    """Minimal GitHub repository response for owner-filter tests."""

    def __init__(self, full_name: str, fork: bool = False) -> None:
        self.full_name = full_name
        self.name = full_name.rsplit("/", maxsplit=1)[1]
        self.fork = fork


class StubGithub3:
    """Records the repository listing arguments used by the linter."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def repositories_by(self, username: str, type: str) -> list[StubRepo]:
        self.calls.append((username, type))
        return [StubRepo(f"{username}/repository"), StubRepo(f"{username}/fork", fork=True)]


def test_get_all_user_repos_scopes_each_request_to_configured_owner() -> None:
    """Configured owners must be sent as usernames, never as a repository type."""
    github3 = StubGithub3()
    linter = object.__new__(GithubLinter)
    linter.github3 = github3
    config = {"linter": {"owner_list": ["yaleman", "terminaloutcomes"]}}

    result = get_all_user_repos(linter, config)

    assert result == ["yaleman/repository", "terminaloutcomes/repository"]
    assert github3.calls == [("yaleman", "owner"), ("terminaloutcomes", "owner")]


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
