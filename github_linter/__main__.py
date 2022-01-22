""" cli bits """

# from typing import List, Dict, Any

import click

# from github.Repository import Repository

from loguru import logger

from . import GithubLinter, search_repos
from .tests import MODULES

# TODO: check for .github/workflows/ dir
# TODO: check for .github/dependabot.yml config

MODULE_CHOICES = [
    key for key in list(MODULES.keys()) if not key.startswith("github_linter")
]


@click.command()
@click.option("--repo", "-r", multiple=True, help="Filter repos")
@click.option("--owner", "-o", multiple=True, help="Filter owners")
@click.option(
    "--module",
    "-m",
    multiple=True,
    type=click.Choice(MODULE_CHOICES),
    help="Specify which modules to run",
)
@click.option(
    "--no-progress",
    is_flag=True,
    default=False,
    help="Hide progress if more than three repos to handle.",
)
@click.option(
    "--fix", "-f", is_flag=True, default=False, help="Take actions to fix things."
)
@click.option(
    "--check", "-k", multiple=True, help="Filter by check name, eg check_example"
)
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

    for index, repo in enumerate(repos):
        if not repo.parent:
            github.handle_repo(repo, check=kwargs.get("check"), fix=kwargs["fix"])
        # if it's a fork and you're checking them
        elif repo.parent.owner.login != user.login and github.config.get("check_forks"):
            github.handle_repo(repo, check=kwargs.get("check"), fix=kwargs["fix"])
        else:
            logger.warning(
                "check_forks is false and {} is a fork, skipping.", repo.full_name
            )
        if len(repos) > 3 and not kwargs.get("no_progress"):
            pct_done = round((index / len(repos) * 100), 1)
            logger.info(
                "Completed {}, {}% ({}/{})",
                repo.full_name,
                pct_done,
                index + 1,
                len(repos),
            )
    github.display_report()


if __name__ == "__main__":
    cli()
