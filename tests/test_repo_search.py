""" testing the search filter generator """

from github_linter import filter_by_repo, generate_repo_search_string
from tests.utils import generate_test_repo


def test_filter_by_repo() -> None:
    """ testing the repo filter """

    repolist = [
        generate_test_repo()
    ]

    result = filter_by_repo(repolist, ["test*"])

    assert result == repolist

    result = filter_by_repo(repolist, ["test1"])
    assert result == repolist

    result = filter_by_repo(repolist, ["test1231"])
    assert not result

    result = filter_by_repo(repolist, ["*1"])
    assert result == repolist

    result = filter_by_repo(repolist, ["test*"])
    assert result == repolist

    result = filter_by_repo(repolist, ["notit*"])
    assert not result


def test_generate_repo_search_string() -> None:
    """ testing generate_repo_search_string """

    owner_filter = [ "yaleman", "terminaloutcomes"]
    result = generate_repo_search_string(repo_filter=["*"], owner_filter=owner_filter)
    assert result.needs_post_filtering
    assert result.search_string == "user:yaleman user:terminaloutcomes"

    owner_filter = [ "yaleman", "terminaloutcomes "]
    result = generate_repo_search_string(repo_filter=["*"], owner_filter=owner_filter)
    assert result.needs_post_filtering
    assert result.search_string == "user:yaleman user:terminaloutcomes"

    owner_filter = [ "yaleman", "terminaloutcomes "]
    repo_filter = ["github_linter", "cheese"]
    result = generate_repo_search_string(repo_filter=repo_filter, owner_filter=owner_filter)
    assert result.search_string == "repo:yaleman/github_linter repo:yaleman/cheese repo:terminaloutcomes/github_linter repo:terminaloutcomes/cheese"
