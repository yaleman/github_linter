"""test the web interface a bit"""

from fastapi.testclient import TestClient
from sqlalchemy.dialects import sqlite

from github_linter.web import app, get_repos_query

client = TestClient(app)


def test_read_main() -> None:
    """test that the home page renders"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>Github Linter</title>" in response.content


def test_repo_query_respects_linter_config() -> None:
    """The cached web view must not expose repos outside configured owners or forks."""
    query = get_repos_query(
        {
            "linter": {
                "owner_list": ["yaleman", "terminaloutcomes"],
                "check_forks": False,
            }
        }
    )

    compiled = str(query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))

    assert "repos.owner IN ('yaleman', 'terminaloutcomes')" in compiled
    assert "repos.fork IS 0" in compiled
