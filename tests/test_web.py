"""test the web interface a bit"""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import create_async_engine

from github_linter.web import DbPaths, create_db, get_app, get_repos_query


@pytest.fixture(scope="function")
def client(tmp_path: str) -> TestClient:
    async def inner_fixture():
        db_paths = DbPaths(Path(tmp_path) / "test.sqlite")
        engine = create_async_engine(db_paths.db_url())
        await create_db(engine, db_paths)
        return TestClient(get_app(engine))

    return asyncio.run(inner_fixture())


@pytest.mark.asyncio
async def test_read_main(client: TestClient) -> None:
    """test that the home page renders"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>Github Linter</title>" in response.content


@pytest.mark.asyncio
async def test_updated(client: TestClient) -> None:
    """test that the updated page renders"""

    response = client.get("/db/updated")
    assert response.status_code == 200
    assert response.text == "-1"


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

    assert "lower(repos.owner) IN ('yaleman', 'terminaloutcomes')" in compiled
    assert "repos.fork IS 0" in compiled
