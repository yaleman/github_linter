""" cli bits """

# from typing import List, Dict, Any

import click

# from github.Repository import Repository

from loguru import logger

from . import GithubLinter, search_repos
from .tests import MODULES

# TODO: check for .github/workflows/ dir
# TODO: check for .github/dependabot.yml config

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
@click.option("--fix", "-f", is_flag=True, default=False, help="Take actions to fix things.")
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
            github.handle_repo(repo, check=kwargs.get("check"), fix=kwargs["fix"])
        # if it's a fork and you're checking them
        elif repo.parent.owner.login != user.login and github.config.get("check_forks"):
            github.handle_repo(repo, check=kwargs.get("check"), fix=kwargs["fix"])
        else:
            logger.warning(
                "check_forks is false and {} is a fork, skipping.", repo.full_name
            )
    github.display_report()


if __name__ == "__main__":
    cli()
