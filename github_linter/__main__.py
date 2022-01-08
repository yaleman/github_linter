""" cli bits """

import json
from typing import List, Dict, Any, Optional


import click

# import github
# from github.ContentFile import ContentFile
from github.Repository import Repository
# from github.GithubException import UnknownObjectException
from loguru import logger

from . import GithubLinter
from .pyproject import check_pyproject_toml
from .dependabot import check_dependabot_config
from .utils import check_files_to_remove
from .types import DICTLIST

# TODO: add cli filter for repo
# TODO: add cli fliter for org/user (owner)

MODULES = {
    "check_files" : check_files_to_remove,
    "pyproject" : check_pyproject_toml,
    "dependabot" : check_dependabot_config,
}



def handle_repo(
    github_object: GithubLinter,
    repo: Repository,
    enabled_modules: Optional[List[str]],
    ):
    """ does things """
    # logger.info("owner: {}", repo.owner)
    logger.info(repo.full_name)
    # logger.info("Blobs URL: {}", repo.blobs_url)

    errors: DICTLIST = {}
    warnings: DICTLIST = {}
    if repo.parent:
        logger.warning("Parent: {}", repo.parent.full_name)

    if enabled_modules:
        for module in enabled_modules:
            if module not in MODULES:
                logger.error("Module not found: {}", module)
            else:
                MODULES[module](github_object, repo, errors, warnings)
    else:
        for module in MODULES:
            MODULES[module](github_object, repo, errors, warnings)

    # check_pyproject_toml(github_object, repo, errors, warnings)
    # check_dependabot_config(github_object, repo, errors, warnings)
    if errors:
        logger.error(json.dumps(errors, indent=4, ensure_ascii=False))
    if warnings:
        logger.warning(json.dumps(warnings, indent=4, ensure_ascii=False))

    if not errors or warnings:
        logger.info("{} all good", repo.full_name)



# TODO: check for pyproject.toml
# TODO: check for .pylintrc
# TODO: check for .drone.yml
# TODO: sanity check... stuff?

# TODO: check for .github/workflows/ dir
# TODO: check for .github/dependabot.yml config

def search_repos(github: GithubLinter, kwargs_object: Dict[str, Dict[Any, Any]]) -> List[Repository]:
    """ search repos based on cli input """
    if kwargs_object.get("repo") or kwargs_object.get("owner"):
        search = ""
        searchrepos = []
        if kwargs_object.get("repo"):
            for repo in kwargs_object["repo"]:
                if kwargs_object.get("owner"):
                    for owner in kwargs_object["owner"]:
                        searchrepos.append(f"{owner}/{repo}")
                else:
                    searchrepos.append(repo)
        else:
            searchrepos = [f"user:{owner}" for owner in kwargs_object["owner"]]
        search = " OR ".join(searchrepos)
        logger.debug("Search string: '{}'", search)
        repos = github.github.search_repositories(query=search)
    else:
        repos = github.github.get_user().get_repos()
    return repos

@click.command()
@click.option("--repo", "-r", multiple=True, help="Filter repos")
@click.option("--owner", "-o", multiple=True, help="Filter owners")
@click.option("--module", "-m", multiple=True, help="Check modules")
def cli(**kwargs):
    """ cli interface """
    github = GithubLinter()
    # logger.debug("Getting user")
    # user = github.github.get_user()
    # logger.info(dir(user))

    logger.debug("Getting repos")

    repos = search_repos(github, kwargs)

    if "module" in kwargs:
        module: List[str] = kwargs["module"]
    else:
        module = None


    for repo in repos:
        handle_repo(github, repo, module)


if __name__ == "__main__":
    cli()
