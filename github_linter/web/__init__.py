""" web interface for the project that outgrew its intention """

import asyncio

import logging
from pathlib import Path
from time import time
from typing import AsyncGenerator, List, Optional


from loguru import logger
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy.dialects.sqlite

from fastapi import  BackgroundTasks, FastAPI, Depends
from fastapi.concurrency import run_in_threadpool

from fastapi.responses import HTMLResponse, FileResponse, Response

from pydantic import BaseModel


from .. import GithubLinter, Repository, get_all_user_repos

DB_PATH = Path("~/.config/github_linter.sqlite").expanduser().resolve()
DB_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"

engine = create_async_engine(DB_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

app = FastAPI()

# pylint: disable=too-few-public-methods
class SQLRepos(Base):
    """ sqlrepos """
    __tablename__ = "repos"
    # "repos",
    # metadata_obj,
    full_name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(255))
    owner = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    default_branch = sqlalchemy.Column(sqlalchemy.String(255))
    archived = sqlalchemy.Column(sqlalchemy.Boolean)
    fork = sqlalchemy.Column(sqlalchemy.Boolean)
    private = sqlalchemy.Column(sqlalchemy.Boolean)
    description = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    open_issues = sqlalchemy.Column(sqlalchemy.Integer)
    last_updated = sqlalchemy.Column(sqlalchemy.Float)
    organization = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    parent = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)

# pylint: disable=too-few-public-methods
class SQLMetadata(Base):
    """ metadata """
    __tablename__ = "metadata"
    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String)

async def create_db():
    """ do the stupid thing """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """ session factory """
    async with async_session_maker() as session:
        yield session


class RepoData(BaseModel):
    """ repo data object """
    full_name: str
    name: str
    owner: Optional[str]
    default_branch: str
    archived: bool
    description: Optional[str]
    fork: bool
    open_issues: int
    last_updated: float
    private: bool
    organization: Optional[str]
    parent: Optional[str]

    class Config:
        """ config """
        orm_mode=True

class MetaData(BaseModel):
    """ system metadata """
    name: str
    value: str
    class Config:
        """ config """
        orm_mode=True


def githublinter_factory():
    """ githublinter factory """
    githublinter = GithubLinter()
    githublinter.do_login()
    yield githublinter

@app.get("/favicon.svg")
async def favicon():
    """ return a """
    icon_file = Path(Path(__file__).resolve().parent.as_posix()+"/images/github.svg")
    if icon_file.exists():
        return FileResponse(icon_file)
    return Response(status_code=404)

@app.get('/css/{filename:str}')
async def css_file(filename: str):
    """ css returner """
    cssfile = Path(Path(__file__).resolve().parent.as_posix()+f"/css/{filename}")
    if cssfile.exists():
        return FileResponse(cssfile)
    return Response(status_code=404)

@app.get("/github_linter.js")
async def github_linter_js():
    """ load the js """
    jspath = Path(Path(__file__).resolve().parent.as_posix()+"/github_linter.js")
    # print(jspath.as_posix())
    if jspath.exists():
        return FileResponse(jspath)
    return Response(status_code=404)



@app.get("/db/updated")
async def db_updated(
    session: AsyncSession = Depends(get_async_session)
    ):
    """ pulls the last_updated field from the db """

    try:
        stmt = sqlalchemy.select(SQLMetadata).where(SQLMetadata.name=="last_updated")
        result: sqlalchemy.engine.result.Result = await session.execute(stmt)

        if result is None:
            logger.debug("No response from db")
            return -1
        row =  result.fetchone()

        if row is None:
            logger.error("no row data querying update time: {}", row)
            return -1
        data = MetaData.from_orm(row["SQLMetadata"])
        return data.value
    # pylint: disable=broad-except
    except Exception as error_message:
        print(f"Failed to pull last_updated: {error_message}")
        return -1

async def update_stored_repo(
    repo: Repository
) -> None:
    """ updates a single repository """
    async with engine.begin() as conn:
        repoobject = RepoData.parse_obj({
            "full_name" : repo.full_name,
            "name" : repo.name,
            "owner" : repo.owner.name,
            "organization" : repo.organization.name if repo.organization else None,
            "default_branch" : repo.default_branch,
            "archived" : repo.archived,
            "description" : repo.description,
            "fork" : repo.fork,
            "open_issues" : repo.open_issues_count,
            "last_updated" : time(),
            "private" : repo.private,
            "parent" :repo.parent.full_name if repo.parent else None,
        })

        insert_row = sqlalchemy.dialects.sqlite.insert(SQLRepos)\
            .values(**repoobject.dict())
        do_update = insert_row.on_conflict_do_update(
            index_elements=['full_name'],
            set_= repoobject.dict(),
        )
        await conn.execute(do_update)
        # await conn.commit()
        logger.info(f"Done with {repo}")
        lastupdated = {"name" : "last_updated", "value" : time()}
        insert_row = sqlalchemy.dialects.sqlite.insert(SQLMetadata)\
            .values(**lastupdated)
        do_update = insert_row.on_conflict_do_update(
            index_elements=['name'],
            set_= lastupdated,
        )
        await conn.execute(do_update)
        await conn.commit()

async def update_stored_repos(
    ) -> None:
    """ background task that caches the results of get_all_user_repos """
    githublinter = GithubLinter()
    base = declarative_base()

    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)

        github_repos: List[Repository]  = get_all_user_repos(githublinter)
        repo_names = [ ghrepo.full_name for ghrepo in github_repos ]

        logger.info(f"Got {len(repo_names)} repos")
        for repo in github_repos:
            await update_stored_repo(repo)

        all_repos_query = sqlalchemy.select(SQLRepos)
        all_repos_execute = await conn.execute(all_repos_query)
        if all_repos_execute is None:
            return None
        allrepos_rows = all_repos_execute.fetchall()
        for dbrepo in allrepos_rows:
            logger.debug("Checking {} for removal.", dbrepo.full_name)
            if dbrepo.full_name not in repo_names:
                logger.info("Removing unlisted repo: {}", dbrepo.full_name)
                deleterepo_query = sqlalchemy.delete(SQLRepos).where(SQLRepos.full_name==dbrepo.full_name)
                await conn.execute(deleterepo_query)




@app.get("/repos/update")
async def update_repos(
    background_tasks: BackgroundTasks,
    ):
    """ does the background thing """

    print("Spawning an update process...")
    background_tasks.add_task(update_stored_repos)

    return {"message": "Updating in the background"}

@app.get("/repos")
async def get_repos(
    session: AsyncSession = Depends(get_async_session)
):
    """ endpoint to provide the cached repo list """

    stmt = sqlalchemy.select(SQLRepos).where(SQLRepos.full_name!="asdfasdfsadfsdaf")
    result = await session.execute(stmt)

    return [ RepoData.from_orm(element["SQLRepos"]) for element in result.fetchall() ]



@app.get("/")
async def root(
    background_tasks: BackgroundTasks,
    ):
    """ homepage """

    background_tasks.add_task(
            create_db,
            )
    indexpath = Path(Path(__file__).resolve().parent.as_posix()+"/index.html")
    # print(indexpath.as_posix())
    if indexpath.exists():
        return HTMLResponse(indexpath.read_bytes())
    return Response(status_code=404)
