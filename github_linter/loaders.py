""" file loading utility function """

from loguru import logger
import yaml

from . import GithubLinter

from .utils import DICTLIST

def load_yaml_file(
    github_object: GithubLinter,
    filename: str,
    _: DICTLIST,
    __: DICTLIST,
    ):
    """ loads a YAML file into a dict """

    fileresult = github_object.cached_get_file(filename)
    if not fileresult:
        return {}
    try:
        filecontents = yaml.load(
            fileresult.decoded_content.decode("utf-8"),
            Loader=yaml.CLoader,
            )
        return filecontents
    except yaml.YAMLError as exc:
        logger.error("Failed to parse dependabot config: {}", exc)
        # add_result(errors_object , "yaf"Failed to parse dependabot config: {exc}")
    return {}
