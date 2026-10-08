import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from github.Repository import Repository
from github.Requester import Requester
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from github_linter.utils import setup_logging
from github_linter.web import AppLifeSpan, DbPaths, create_db, get_updated, set_update_time, update_stored_repo

setup_logging(True)


@pytest.fixture(scope="function")
def dbfixture(tmp_path: str) -> tuple[DbPaths, AsyncEngine]:
    async def inner_fixture():
        db_paths = DbPaths(Path(tmp_path) / "test.sqlite")
        engine = create_async_engine(db_paths.db_url())
        await create_db(engine, db_paths)
        return (db_paths, engine)

    return asyncio.run(inner_fixture())


@pytest.mark.asyncio
async def test_db_actions(dbfixture: tuple[DbPaths, AsyncEngine]):
    setup_logging(True)
    db_paths, engine = dbfixture

    assert (db_paths.DB_PATH).exists()
    async with engine.begin() as conn:
        assert await get_updated(conn) == -1
    async with engine.begin() as conn:
        await set_update_time(12345, conn)
    async with engine.begin() as conn:
        assert await get_updated(conn) == 12345


@pytest.mark.asyncio
async def test_lifetime(dbfixture: tuple[DbPaths, AsyncEngine]):
    setup_logging(True)
    db_paths, engine = dbfixture
    app = FastAPI(lifespan=AppLifeSpan(engine).lifespan)
    async with app.router.lifespan_context(app):
        assert (db_paths.DB_PATH).exists()


@pytest.mark.asyncio
async def test_update_stored_repo(dbfixture: tuple[DbPaths, AsyncEngine]):
    setup_logging(True)
    _db_paths, engine = dbfixture
    requester = Requester(lazy=True, auth=None, base_url="http://example.com", timeout=5, user_agent="test", per_page=1, verify=False, retry=None, pool_size=None)
    repo = Repository(
        attributes={
            "full_name": "test/repo",
            "name": "repo",
            "owner": {"login": "owner"},
            "organization": None,
            "default_branch": "main",
            "archived": False,
            "description": "A test repo",
            "fork": False,
            "open_issues_count": 0,
            "private": False,
            "parent": None,
            "requester": requester,
            "headers": {"Cheese": "Cheddar"},
        },
        requester=requester,
    )
    await update_stored_repo(repo=repo, dbengine=engine, do_update=False)
