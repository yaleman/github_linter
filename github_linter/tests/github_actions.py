""" github actions tests """

# import yaml
import json5 as json
from loguru import logger

from .. import RepoLinter

from ..loaders import load_yaml_file

CATEGORY = "github_actions"

LANGUAGES = [ "all" ]

#https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone


def check_configuration_required_fields(
    repo: RepoLinter
) -> None:
    """ Checks that all the *required* fields exist """

    filename = ".github/workflows/testing.yml"
    config_file = load_yaml_file(repo, filename)

    logger.debug(json.dumps(config_file, indent=4))
    if not config_file:
        return repo.add_error(
            CATEGORY,
            f"Couldn't find/load github actions file: {filename}"
        )

    for required_key in [
        "name",
        "on",
        "jobs",
    ]:
        if required_key not in config_file:
            repo.add_error(CATEGORY, f"Missing key in action config: {required_key}")
    return None
