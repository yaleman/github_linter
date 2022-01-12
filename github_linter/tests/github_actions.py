""" github actions tests """

# import yaml
import json5 as json
from loguru import logger

from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..utils import DICTLIST, add_result
from ..loaders import load_yaml_file

CATEGORY = "github_actions"

LANGUAGES = [ "all" ]

#https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/configuration-options-for-dependency-updates#scheduletimezone


def check_configuration_required_fields(
    github_object: GithubLinter,
    errors_list: DICTLIST,
    warnings_list: DICTLIST,
) -> None:
    """ Checks that all the *required* fields exist """

    if not github_object.current_repo:
        raise RepositoryNotSet

    filename = ".github/workflows/testing.yml"
    config_file = load_yaml_file(github_object, filename, errors_list, warnings_list)

    logger.debug(json.dumps(config_file, indent=4))
    if not config_file:
        return add_result(
            errors_list,
            CATEGORY,
            f"Couldn't find/load github actions file: {filename}"
        )

    for required_key in [
        "name",
        "on",
        "jobs",
    ]:
        if required_key not in config_file:
            add_result(errors_list, CATEGORY, f"Missing key in action config: {required_key}")
