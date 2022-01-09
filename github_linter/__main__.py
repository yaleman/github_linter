""" cli bits """

from typing import List, Dict, Any
from inspect import ismodule

import click

# import github
# from github.ContentFile import ContentFile
from github.Repository import Repository

# from github.GithubException import UnknownObjectException
from loguru import logger

from . import GithubLinter

# from .utils import check_files_to_remove
from .types import DICTLIST

# all the tests
#
# from .tests.pyproject import check_pyproject_toml
from .tests import generic, dependabot, issues, pylintrc, pyproject

MODULES = {
    "dependabot": dependabot,
    "generic": generic,
    "issues": issues,
    "pylintrc": pylintrc,
    "pyproject": pyproject,
}


def run_module(
    github_object: GithubLinter,
    repo_object: Repository,
    errors_object: DICTLIST,
    warnings_object: DICTLIST,
    module: str,
) -> bool:
    """ runs a module after checking what it is """
    if module not in MODULES:
        logger.error("Module not found: {}", module)
        return False
    if not ismodule(MODULES[module]):
        raise TypeError(f"Found type {type(MODULES[module])} while running module.")
    for check in dir(MODULES[module]):
        if check.startswith("check_"):
            logger.debug("Running {}", check)
            getattr(MODULES[module], check)(
                github_object, repo_object, errors_object, warnings_object
            )
    return True


def handle_repo(
    github_object: GithubLinter,
    repo: Repository,
    enabled_modules: List[str],
):
    """ does things """
    # logger.info("owner: {}", repo.owner)
    logger.debug(repo.full_name)
    if repo.archived:
        logger.warning("Repository is archived!")
    # logger.info("Blobs URL: {}", repo.blobs_url)

    errors: DICTLIST = {}
    warnings: DICTLIST = {}
    if repo.parent:
        logger.warning("Parent: {}", repo.parent.full_name)

    if not enabled_modules:
        enabled_modules = list(MODULES.keys())
    for module in enabled_modules:
        run_module(github_object, repo, errors, warnings, module)

    # check_pyproject_toml(github_object, repo, errors, warnings)
    # check_dependabot_config(github_object, repo, errors, warnings)
    # if errors:
    #     logger.error(json.dumps(errors, indent=4, ensure_ascii=False))
    # if warnings:
    #     logger.warning(json.dumps(warnings, indent=4, ensure_ascii=False))

    if not errors or warnings:
        logger.debug("{} all good", repo.full_name)
    github_object.report[repo.full_name] = {
        "errors" : errors,
        "warnings" : warnings,
    }

# TODO: sanity check... stuff?

# TODO: check for .github/workflows/ dir
# TODO: check for .github/dependabot.yml config
# TODO: disable modules based on #repo.get_languages...
# TODO: add tests to make sure all modules have CATEGORY and LANGUAGES set

def search_repos(
    github: GithubLinter, kwargs_object: Dict[str, Dict[Any, Any]]
) -> List[Repository]:
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
        search_result = github.github.search_repositories(query=search)

        # filter search results by owner
        if kwargs_object.get("owner"):
            # logger.debug("Filtering based on owner: {}", kwargs_object["owner"])
            filtered_result = [
                repo
                for repo in search_result
                if repo.owner.login in kwargs_object["owner"]
            ]
            search_result = filtered_result
        # filter search results by repo name
        if kwargs_object.get("repo"):
            # logger.debug("Filtering based on repo: {}", kwargs_object["repo"])
            filtered_result = [
                repo for repo in search_result if repo.name in kwargs_object["repo"]
            ]
            search_result = filtered_result
        return search_result

    return github.github.get_user().get_repos()


@click.command()
@click.option("--repo", "-r", multiple=True, help="Filter repos")
@click.option("--owner", "-o", multiple=True, help="Filter owners")
@click.option(
    "--module",
    "-m",
    multiple=True,
    type=click.Choice(list(MODULES.keys())),
    help="Specify which modules to run",
)
def cli(**kwargs):
    """ Github linter for checking your repositories for various things. """
    github = GithubLinter()

    logger.debug("Getting repos")
    repos = search_repos(github, kwargs)

    if "module" in kwargs:
        module: List[str] = kwargs["module"]
    else:
        module = list(MODULES.keys())

    user = github.github.get_user()

    if github.config.get("check_forks"):
        logger.debug("Checking forks")

    for repo in repos:
        if not repo.parent:
            handle_repo(github, repo, module)
        # if it's a fork and you're checking them
        elif repo.parent.owner.login != user.login and github.config.get("check_forks"):
            handle_repo(github, repo, module)
        else:
            logger.warning(
                "check_forks is true and {} is a fork, skipping.", repo.full_name
            )
    github.display_report()

if __name__ == "__main__":
    cli()
