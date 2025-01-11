"""cli bits"""

from typing import List, Optional, Tuple

import click
from loguru import logger

from . import GithubLinter, search_repos
from .utils import setup_logging
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
@click.option("--list-repos", is_flag=True, default=False, help="List repos and exit")
@click.option("--debug", "-d", is_flag=True, default=False, help="Enable debug logging")
# pylint: disable=too-many-arguments,too-many-locals
def cli(
    repo: Optional[Tuple[str]] = None,
    owner: Optional[Tuple[str]] = None,
    fix: bool = False,
    check: Optional[Tuple[str]] = None,
    no_progress: bool = False,
    debug: bool = False,
    module: Optional[List[str]] = None,
    list_repos: bool = False,
) -> None:
    """Github linter for checking your repositories for various things."""

    setup_logging(debug)
    load_modules(module)

    github = GithubLinter()

    # these just set defaults
    repo_filter = (
        [] if repo is None else [element for element in repo if element is not None]
    )
    owner_filter = (
        [] if owner is None else [element for element in owner if element is not None]
    )

    logger.debug("Getting repos")
    repos = search_repos(github, repo_filter, owner_filter)

    # doing the type-ignore thing here because "x.full_name" can be assumed to exist, but is typed as Any
    # and this makes mypy sad.
    repos.sort(key=lambda x: x.full_name)
    if list_repos:
        for repo_lister in repos:
            logger.info(repo_lister.full_name)
        return

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
    for module_name in github.modules:
        logger.info("- {}", module_name)

    for index, repository in enumerate(repos):
        if repository.fork and not github.config.get("check_forks"):
            logger.warning(
                "check_forks is false and {} is a fork, skipping.", repository.full_name
            )
            continue
        github.handle_repo(repository, check=check, fix=fix)

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
