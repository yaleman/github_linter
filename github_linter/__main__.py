""" cli bits """

import sys
from typing import List, Optional, Tuple

import click
from loguru import logger

from . import GithubLinter, search_repos
from .tests import MODULES, load_modules

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
    help="Specify which modules to run, allows multiple.",
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
@click.option(
    "--debug", "-d", is_flag=True, default=False, help="Enable debug logging"
)
# pylint: disable=too-many-arguments,too-many-locals
def cli(
    repo: Optional[Tuple[str]] = None,
    owner: Optional[Tuple[str]] = None,
    fix: bool = False,
    check: Optional[Tuple[str]] = None,
    no_progress: bool = False,
    debug: bool = False,
    module: Optional[List[str]] = None,
    ) -> None:
    """ Github linter for checking your repositories for various things. """

    if not debug:
        logger.remove()
        logger.add(level="INFO", sink=sys.stdout)

    load_modules(module)

    github = GithubLinter()

    # these just set defaults
    repo_filter = [] if repo is None else [ element for element in repo if element is not None ]
    owner_filter = [] if owner is None else [ element for element in owner if element is not None ]

    user = github.github.get_user()

    logger.debug("Getting repos")
    repos = search_repos(github, repo_filter, owner_filter)

    if not repos:
        return

    if module and len(module) > 0:
        for selected_module in module:
            github.add_module(selected_module, MODULES[selected_module])
    else:
        logger.debug("Running all available modules.")
        for selected_module in MODULES:
            github.add_module(selected_module, MODULES[selected_module])

    if not github.modules:
        logger.error("No modules configured, bailing!")
        return
    logger.info("Listing activated modules:")
    for module in github.modules:
        logger.info("- {}", module)

    for index, repository in enumerate(repos):
        if not repository.parent:
            github.handle_repo(repository, check=check, fix=fix)
        # if it's a fork and you're checking them
        elif repository.parent.owner.login != user.login and github.config.get("check_forks"):
            github.handle_repo(repository, check=check, fix=fix)
        else:
            logger.warning(
                "check_forks is false and {} is a fork, skipping.", repository.full_name
            )
        if len(repos) > 3 and not no_progress:
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
