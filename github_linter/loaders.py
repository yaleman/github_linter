""" file loading utility function """

from typing import Any, Dict, Optional

from loguru import logger
from ruyaml import YAML

from . import RepoLinter

def load_yaml_file(
    repo: RepoLinter,
    filename: str,
) -> Optional[Dict[Any,Any]]:
    """ loads a YAML file into a dict """

    fileresult = repo.cached_get_file(filename)
    if not fileresult:
        return {}
    try:
        filecontents = YAML(pure=True).load(fileresult.decoded_content.decode("utf-8"))
        return filecontents
    #pylint: disable=broad-except
    except Exception as error_message:
        logger.error("Failed to parse yaml file {}: {}", filename, error_message)
        # TODO: Catch a better exception in loaders.load_yaml_file
    return None
