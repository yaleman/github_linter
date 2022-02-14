""" cli for the web interface for the project that outgrew its intention """

import asyncio
from typing import List
from time import time

import click
from github.Repository import Repository

import sqlalchemy

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
import sqlalchemy.dialects.sqlite

import uvicorn # type: ignore

from .. import GithubLinter, get_all_user_repos

from . import DB_URL, RepoData, SQLMetadata, SQLRepos

@click.command()
@click.option("--reload", is_flag=True)
@click.option("--port", type=int, default=8000)
@click.option("--host", type=str, default="0.0.0.0")
@click.option("--proxy-headers", is_flag=True)
@click.option("--update", "-u", is_flag=True)
def cli(
    reload: bool=False,
    port: int=8000,
    host: str="0.0.0.0",
    proxy_headers: bool=False,
    update: bool=False,
    ):
    """ github_linter server """
    if update:
        asyncio.run(update_stored_repos())
    else:
        uvicorn.run(
            app="github_linter.web:app",
            reload=reload,
            host=host,
            port=port,
            proxy_headers=proxy_headers,
            workers=4,
            )

async def update_stored_repos(
    ):
    """ background task that caches the results of get_all_user_repos """
    githublinter = GithubLinter()

    engine = create_async_engine(DB_URL, echo=False)
    base = declarative_base()
    # async_session = sessionmaker(
    #     engine, class_=AsyncSession, expire_on_commit=False
    # )

    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)




    # with async_session() as session:
    results: List[Repository]  = get_all_user_repos(githublinter)

    print(f"Got {len(results)} repos")
    for repo in results:
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
            print(f"Done with {repo}")
            lastupdated = {"name" : "last_updated", "value" : time()}
            insert_row = sqlalchemy.dialects.sqlite.insert(SQLMetadata)\
                .values(**lastupdated)
            do_update = insert_row.on_conflict_do_update(
                index_elements=['name'],
                set_= lastupdated,
            )
            await conn.execute(do_update)
            await conn.commit()


if __name__ == '__main__':
    cli()
