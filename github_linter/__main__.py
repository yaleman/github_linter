""" cli bits """

from typing import List, Optional, Tuple

import click
from loguru import logger

from . import GithubLinter, search_repos
from .tests import MODULES

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
def cli(
    repo: Optional[Tuple[str]] = None,
    owner: Optional[Tuple[str]] = None,
    **kwargs):
    """ Github linter for checking your repositories for various things. """
    github = GithubLinter()

    if repo is None or len(repo) == 0:
        repo_filter: List[str] = []
    else:
        repo_filter = list(repo)

    if owner is None or len(owner) == 0:
        owner_filter: List[str] = []
    else:
        owner_filter = list(owner)

    user = github.github.get_user()

    logger.debug("Getting repos")
    repos = search_repos(github, repo_filter, owner_filter)


    if "module" in kwargs and len(kwargs["module"]) > 0:
        for module in kwargs["module"]:
            github.add_module(module, MODULES[module])
    else:
        logger.debug("Running all available modules.")
        for module in MODULES:
            github.add_module(module, MODULES[module])

    for index, repository in enumerate(repos):
        if not repository.parent:
            github.handle_repo(repository, check=kwargs.get("check"), fix=kwargs["fix"])
        # if it's a fork and you're checking them
        elif repository.parent.owner.login != user.login and github.config.get("check_forks"):
            github.handle_repo(repository, check=kwargs.get("check"), fix=kwargs["fix"])
        else:
            logger.warning(
                "check_forks is false and {} is a fork, skipping.", repository.full_name
            )
        if len(repos) > 3 and not kwargs.get("no_progress"):
            pct_done = round((index / len(repos) * 100), 1)
            logger.info(
                "Completed {}, {}% ({}/{})",
                repository.full_name,
                pct_done,
                index + 1,
                len(repos),
            )
    github.display_report()


if __name__ == "__main__":
    cli()
