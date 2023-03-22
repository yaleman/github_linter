""" web interface for the project that outgrew its intention """

from pathlib import Path
from time import time
from typing import Any, AsyncGenerator, Generator, List, Optional, Union

from fastapi import  BackgroundTasks, FastAPI, Depends
from fastapi.responses import HTMLResponse, FileResponse, Response
from github.Repository import Repository
from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger
from pydantic import BaseModel
import sqlalchemy
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base
#, sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker

import sqlalchemy.dialects.sqlite

__all__ = [
    "get_all_user_repos",
]

from .. import GithubLinter, get_all_user_repos

DB_PATH = Path("~/.config/github_linter.sqlite").expanduser().resolve()
DB_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"

engine = create_async_engine(DB_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

app = FastAPI()

# pylint: disable=too-few-public-methods
class SQLRepos(Base):
    """ sqlrepos """
    __tablename__ = "repos"
    full_name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(255))
    owner = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    default_branch = sqlalchemy.Column(sqlalchemy.String(255))
    archived = sqlalchemy.Column(sqlalchemy.Boolean)
    fork = sqlalchemy.Column(sqlalchemy.Boolean)
    private = sqlalchemy.Column(sqlalchemy.Boolean)
    description = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    open_issues = sqlalchemy.Column(sqlalchemy.Integer)
    open_prs = sqlalchemy.Column(sqlalchemy.Integer)
    last_updated = sqlalchemy.Column(sqlalchemy.Float)
    organization = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    parent = sqlalchemy.Column(sqlalchemy.String(255), nullable=True)

# pylint: disable=too-few-public-methods
class SQLMetadata(Base):
    """ metadata """
    __tablename__ = "metadata"
    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    value = sqlalchemy.Column(sqlalchemy.String)

class MetaData(BaseModel):
    """ system metadata """
    name: str
    value: str
    class Config:
        """ config """
        orm_mode=True

async def create_db() -> None:
    """ do the initial DB creation """
    async with engine.begin() as conn:
        result = await conn.run_sync(Base.metadata.create_all)
        logger.info("Result of creating DB: {}", result)


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
    open_prs: int
    last_updated: float
    private: bool
    organization: Optional[str]
    parent: Optional[str]

    class Config:
        """ config """
        orm_mode=True


def githublinter_factory() -> Generator[GithubLinter, None, None]:
    """ githublinter factory """
    githublinter = GithubLinter()
    githublinter.do_login()
    yield githublinter

async def set_update_time(update_time: float, conn: Any) -> None:
    """ sets the last_updated time in the DB """
    logger.debug("Setting update time to {}", update_time)
    lastupdated = {"name" : "last_updated", "value" : update_time}

    await conn.run_sync(Base.metadata.create_all)
    insert_row = sqlalchemy.dialects.sqlite.insert(SQLMetadata).values(**lastupdated) #type: ignore
    do_update = insert_row.on_conflict_do_update(
        index_elements=['name'],
        set_= lastupdated,
    )
    await conn.execute(do_update)
    await conn.commit()

    logger.debug("Successfully set update time to {}", update_time)


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
            "open_prs" : repo.get_pulls().totalCount,
            "last_updated" : time(),
            "private" : repo.private,
            "parent" :repo.parent.full_name if repo.parent else None,
        })


        insert_row = sqlalchemy.dialects.sqlite.insert(SQLRepos).values(**repoobject.dict()) #type: ignore

        do_update = insert_row.on_conflict_do_update(
            index_elements=['full_name'],
            set_= repoobject.dict(),
        )
        await conn.execute(do_update)
        logger.info("Done with {}", repo.full_name)

        await set_update_time(time(), conn)
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

async def cron_update(
    ) -> None:
    """ background task that does things every so often """
    # githublinter = GithubLinter()
    base = declarative_base()

    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
        last_update = await db_updated()
        if (time() - last_update) >= 3600:
            logger.debug("Cron shows it's been an hour, doing update...")
            await update_stored_repos()
            logger.success("Completed background cron update...")

@app.get("/favicon.svg", response_model=None)
async def favicon() -> Union[Response,FileResponse]:
    """ return a """
    icon_file = Path(Path(__file__).resolve().parent.as_posix()+"/images/github.svg")
    if icon_file.exists():
        return FileResponse(icon_file)
    return Response(status_code=404)

@app.get('/css/{filename:str}', response_model=None)
async def css_file(filename: str) -> Union[Response,FileResponse]:
    """ css returner """
    cssfile = Path(Path(__file__).resolve().parent.as_posix()+f"/css/{filename}")
    if cssfile.exists():
        return FileResponse(cssfile)
    return Response(status_code=404)

@app.get("/github_linter.js", response_model=None)
async def github_linter_js() -> Union[Response,FileResponse]:
    """ load the js """
    jspath = Path(Path(__file__).resolve().parent.as_posix()+"/github_linter.js")
    if jspath.exists():
        return FileResponse(jspath)
    return Response(status_code=404)

@app.get("/db/updated", response_model=None)
async def db_updated(
    ) -> int:
    """ pulls the last_updated field from the db """

    async with engine.begin() as conn:
        try:
            stmt = sqlalchemy.select(SQLMetadata).where(SQLMetadata.name=="last_updated")
            result: sqlalchemy.engine.result.Result = await conn.execute(stmt) #type: ignore

            if result is None:
                logger.debug("No response from db")
                return -1
            row =  result.fetchone()

            if row is None:
                logger.error("no row data querying update time: {}", row)
                return -1
            # print(row)
            data = MetaData.from_orm(row)
            if '.' in data.value:
                return int(data.value.split(".")[0])
        # pylint: disable=broad-except
        except Exception as error_message:
            logger.warning(f"Failed to pull last_updated: {error_message}")
            try:
                await set_update_time(-1, conn)
                await conn.commit()
                logger.success("Set it to -1 instead")
            # pylint: disable=broad-except
            except Exception as error:
                logger.error("Tried to set it to -1 but THAT went wrong too! {}", error)
        return -1

class ResponseMessage(BaseModel):
    """ simple basemodel for response messages """
    message: str

@app.get("/repos/update")
async def update_repos(
    background_tasks: BackgroundTasks,
    ) -> ResponseMessage:
    """ Call this endpoint (/repos/update) to start the update process in the background. """

    logger.info("Spawning an update process...")
    background_tasks.add_task(update_stored_repos)
    return ResponseMessage(message="Updating in the background")

@app.get("/health", response_model=None)
async def get_health(
    background_tasks: BackgroundTasks,
    ) -> Response:
    """ really simple health check, also triggers cron jobs sneakily """

    # let's just check periodically for an update
    background_tasks.add_task(cron_update)

    return Response(content="OK", status_code=200)

@app.get("/repos")
async def get_repos(
    session: AsyncSession = Depends(get_async_session)
) -> List[RepoData]:
    """ endpoint to provide the cached repo list """

    try:
        stmt = sqlalchemy.select(SQLRepos)
        result = await session.execute(stmt)
        retval = [ RepoData.from_orm(element.SQLRepos) for element in result.fetchall() ]
    except OperationalError as operational_error:
        logger.warning("Failed to pull repos from DB: {}", operational_error)
        return []
    return retval


@app.get("/", response_model=None)
async def root(
    background_tasks: BackgroundTasks,
    ) -> Union[Response,HTMLResponse]:
    """ homepage """
    logger.info("Creating background task to create DB.")
    background_tasks.add_task(
            create_db,
            )
    env = Environment(
        loader=PackageLoader(package_name="github_linter.web.templates", package_path=".",),
        autoescape=select_autoescape()
    )
    template = env.get_template("index.html")

    return HTMLResponse(template.render())
