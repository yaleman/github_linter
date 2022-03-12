""" docs tests """

from typing import TypedDict


from jinja2 import Environment, PackageLoader, select_autoescape
import jinja2.exceptions
from loguru import logger

from ..repolinter import RepoLinter


class DefaultConfig(TypedDict):
    """ default config for the test module """
    contributing_file: str

CATEGORY = "docs"
DEFAULT_CONFIG: DefaultConfig = {
    "contributing_file" : ".github/CONTRIBUTING.md"
}
LANGUAGES = [ "ALL" ]

def check_contributing_exists(repo: RepoLinter) -> None:
    """ checks that .github/CONTRIBUTING.md exists """
    # don't need to run this if it's archived
    repo.skip_on_archived()

    filepath: str = repo.config[CATEGORY]["contributing_file"]
    filecontents = repo.cached_get_file(filepath)

    if filecontents is None:
        repo.error(CATEGORY, f"Couldn't find {filepath}")
        return None
    logger.debug("Found {}", filepath)

def fix_contributing_exists(repo:RepoLinter) -> None:
    """ creates a templated file """

    # start up jinja2
    jinja2_env = Environment(
        loader=PackageLoader(package_name="github_linter", package_path="."),
        autoescape=select_autoescape(),
    )
    try:
        template = jinja2_env.get_template(f"fixes/{CATEGORY}/CONTRIBUTING.md")
        new_filecontents = template.render(repo=repo.repository)

    except jinja2.exceptions.TemplateNotFound as template_error:
        logger.error("Failed to load template: {}", template_error)
        return None

    logger.warning("DOCS CONTRIBUTING TEST:")
    logger.info(new_filecontents)
    filepath = repo.config[CATEGORY]["contributing_file"]

    commit_url = repo.create_or_update_file(
        filepath=filepath,
        newfile=new_filecontents,
        message=f"github-linter docs module creating {filepath}",
    )
    repo.fix(CATEGORY, f"Created {filepath}, commit url: {commit_url}")
