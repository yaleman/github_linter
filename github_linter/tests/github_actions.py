""" github actions tests """

from typing import TypedDict

import json5 as json
from loguru import logger

from .. import RepoLinter

from ..loaders import load_yaml_file

CATEGORY = "github_actions"

LANGUAGES = [ "all" ]


class DefaultConfig(TypedDict):
    """ config typing for module config """

DEFAULT_CONFIG: DefaultConfig = {}

#https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone


def check_workflow_dir_exists(repo: RepoLinter):
    """ checks '.github/workflows/' exists """
    if not repo.cached_get_file(".github", clear_cache=True):
        repo.error(CATEGORY, ".github dir not found")
        return

    filename = '.github/workflows/'
    result = repo.cached_get_file(filename, clear_cache=True)

    if not result:
        repo.error(CATEGORY, f"Workflows dir ({filename}) missing.")
        return
    if not result.type == "directory":
        repo.error(CATEGORY, f"Type is wrong for {filename}, should be directory, is {result.type}")


def check_configuration_required_fields(
    repo: RepoLinter
) -> None:
    """ Checks that all the *required* fields exist """

    filename = ".github/workflows/testing.yml"
    config_file = load_yaml_file(repo, filename)


    logger.debug(json.dumps(config_file, indent=4))
    if not config_file:
        return repo.error(
            CATEGORY,
            f"Couldn't find/load github actions file: {filename}"
        )

    for required_key in [
        "name",
        "on",
        "jobs",
    ]:
        if required_key not in config_file:
            repo.error(CATEGORY, f"Missing key in action config: {required_key}")
    return None
