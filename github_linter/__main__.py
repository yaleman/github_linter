""" cli bits """

import json
from typing import List, Dict


import click

# from github.ContentFile import ContentFile
# import github
from github.Repository import Repository
# from github.GithubException import UnknownObjectException
from loguru import logger

from . import GithubLinter
from .pyproject import check_pyproject_toml

# TODO: add cli filter for repo
# TODO: add cli fliter for org/user (owner)


def handle_repo(github_object: GithubLinter, repo: Repository):
    """ does things """
    # logger.info("owner: {}", repo.owner)
    logger.info(repo.full_name)
    # logger.info("Blobs URL: {}", repo.blobs_url)
    if repo.parent:
        logger.warning("Parent: {}", repo.parent.full_name)

    # contents = repo.get_contents("")
    # for content_file in contents:
    #    print(content_file)

    errors: Dict[str, List[str]] = {}
    warnings: Dict[str, List[str]] = {}

    check_pyproject_toml(github_object, repo, errors, warnings)

    if errors or warnings:
        logger.error(json.dumps(errors, indent=4, ensure_ascii=False))
        logger.warning(json.dumps(warnings, indent=4, ensure_ascii=False))
    else:
        logger.info("{} all good", repo.full_name)



# TODO: check for pyproject.toml
# TODO: check for .pylintrc
# TODO: check for .drone.yml
# TODO: sanity check... stuff?

# TODO: check for .github/workflows/ dir
# TODO: check for .github/dependabot.yml config


@click.command()
@click.option("--repo", "-r", multiple=True, help="Filter repos")
@click.option("--owner", "-o", multiple=True, help="Filter owners")
def cli(**kwargs: dict):
    """ cli interface """
    github = GithubLinter()
    logger.debug("Getting user")
    user = github.github.get_user()
    # logger.info(dir(user))

    logger.debug("Getting repos")

    if kwargs.get("repo") or kwargs.get("owner"):
        search = ""
        searchrepos = []
        if kwargs.get("repo"):
            for repo in kwargs["repo"]:
                if kwargs.get("owner"):
                    for owner in kwargs["owner"]:
                        searchrepos.append(f"{owner}/{repo}")
                else:
                    searchrepos.append(repo)
        else:
            searchrepos = [f"user:{owner}" for owner in kwargs["owner"]]
        search = " OR ".join(searchrepos)
        logger.debug("Search string: '{}'", search)
        repos = github.github.search_repositories(query=search)
        logger.debug(list(repos))

    else:
        repos = user.get_repos()

    for repo in repos:
        handle_repo(github, repo)


if __name__ == "__main__":
    cli()
