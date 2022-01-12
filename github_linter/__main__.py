""" cli bits """

from typing import List, Dict, Any

import click

from github.Repository import Repository

from loguru import logger

from . import GithubLinter
from .tests import MODULES



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
        search_result = list(github.github.search_repositories(query=search))

        # filter search results by owner
        if kwargs_object.get("owner"):
            # logger.debug("Filtering based on owner: {}", kwargs_object["owner"])
            filtered_result = [
                repo
                for repo in search_result
                if repo.owner.login in kwargs_object["owner"]
            ]
            search_result = list(filtered_result)
        # filter search results by repo name
        if kwargs_object.get("repo"):
            # logger.debug("Filtering based on repo: {}", kwargs_object["repo"])
            filtered_result = [
                repo for repo in search_result if repo.name in kwargs_object["repo"]
            ]
            return filtered_result
        return search_result

    return list(github.github.get_user().get_repos())


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
@click.option("--check", "-k", multiple=True, help="Filter by check name, eg check_example")
def cli(**kwargs):
    """ Github linter for checking your repositories for various things. """
    github = GithubLinter()

    if "module" in kwargs and len(kwargs["module"]) > 0:
        for module in kwargs["module"]:
            github.add_module(module, MODULES[module])
    else:
        logger.debug("Running all available modules.")
        for module in MODULES:
            github.add_module(module, MODULES[module])

    user = github.github.get_user()

    logger.debug("Getting repos")
    repos = search_repos(github, kwargs)

    for repo in repos:
        if not repo.parent:
            github.handle_repo(repo, kwargs.get("check"))
        # if it's a fork and you're checking them
        elif repo.parent.owner.login != user.login and github.config.get("check_forks"):
            github.handle_repo(repo, kwargs.get("check"))
        else:
            logger.warning(
                "check_forks is true and {} is a fork, skipping.", repo.full_name
            )
    github.display_report()


if __name__ == "__main__":
    cli()
