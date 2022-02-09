""" web interface for the project that outgrew its intention """

from pathlib import Path
from typing import List
from time import time

from fastapi import  BackgroundTasks, FastAPI, Depends
from fastapi.concurrency import run_in_threadpool

from fastapi.responses import HTMLResponse, FileResponse, Response

from github.Repository import Repository
from loguru import logger
from tinydb import TinyDB, Query

from .. import GithubLinter, get_all_user_repos

app = FastAPI()

def githublinter_factory():
    """ githublinter factory """
    githublinter = GithubLinter()
    githublinter.do_login()
    yield githublinter

def tinydb_factory():
    """ factory for configuration of tinydb """
    dbpath = Path("~/.config/github_linter_db.json").expanduser().resolve().as_posix()
    tinydb = TinyDB(dbpath)
    yield tinydb

@app.get("/favicon.ico")
async def favicon_ico():
    """ return a null favicon """

    return FileResponse("")

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
    print(jspath.as_posix())
    if jspath.exists():
        return FileResponse(jspath)
    return Response(status_code=404)

async def update_stored_repos(
    githublinter: GithubLinter=Depends(githublinter_factory),
    tinydb: TinyDB=Depends(tinydb_factory),
    ):
    """ background task that caches the results of get_all_user_repos """
    results: List[Repository]  = await run_in_threadpool(lambda: get_all_user_repos(githublinter))
    repotable = tinydb.table("repo")
    lastupdated = tinydb.table("metadata")
    for repo in results:

        parent = repo.parent.full_name if repo.parent else None
        organization = repo.organization.name if repo.organization else None
        repodata = {
            "full_name" : repo.full_name,
            "name" : repo.name,
            "owner" : repo.owner.name,
            "organization" : organization,
            "default_branch" : repo.default_branch,
            "archived" : repo.archived,
            "description" : repo.description,
            "fork" : repo.fork,
            "id" : repo.id,
            "open_issues" : repo.open_issues_count,
            "last_updated" : time(),
            "private" : repo.private,
            "parent" : parent,

        }
        repotable.upsert(repodata, Query().full_name == repo.full_name)
        logger.debug("Added {}", repo.full_name)
        lastupdated.upsert({"name" : "last_updated", "value" : time()}, Query().name == "last_updated")

@app.get("/db/updated")
async def db_updated(tinydb: TinyDB=Depends(tinydb_factory)):
    """ pulls the last_updated field from the db """
    result = tinydb.table("metadata").get(Query().name=="last_updated")
    if result is None:
        return -1
    return result["value"]

@app.get("/repos/update")
async def update_repos(
    background_tasks: BackgroundTasks,
    githublinter: GithubLinter=Depends(githublinter_factory),
    tinydb: TinyDB=Depends(tinydb_factory),
    ):
    """ does the background thing """
    background_tasks.add_task(
        update_stored_repos,
        githublinter,
        tinydb,
        )
    return {"message": "Updating in the background"}

@app.get("/repos")
async def get_repos(
    tinydb: TinyDB=Depends(tinydb_factory),
):
    """ endpoint to provide the cached repo list """
    repotable = tinydb.table("repo")
    repos = repotable.all()
    return repos


@app.get("/")
async def root():
    """ homepage """
    indexpath = Path(Path(__file__).resolve().parent.as_posix()+"/index.html")
    print(indexpath.as_posix())
    if indexpath.exists():
        return HTMLResponse(indexpath.read_bytes())
    return Response(status_code=404)
