""" test the web interface a bit """

import pytest
from fastapi.testclient import TestClient

from github_linter import GithubLinter
from github_linter.web import app, get_all_user_repos


client = TestClient(app)


def test_read_main() -> None:
    """test that the home page renders"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>Github Linter</title>" in response.content


@pytest.mark.network
def test_get_all_user_repos() -> None:
    """tests what we get back from it"""
    linter = GithubLinter()
    linter.do_login()
    config = {
        "linter": {
            "owner_list": [
                "yaleman",
            ]
        }
    }
    result = get_all_user_repos(linter, config)

    for repo in result:
        print(repo)
    print(f"Found {len(result)} repositories")
