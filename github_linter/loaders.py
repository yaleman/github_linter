"""file loading utility function"""

from typing import Any

from loguru import logger
from ruyaml import YAML

from .repolinter import RepoLinter


def load_yaml_file(
    repo: RepoLinter,
    filename: str,
) -> dict[Any, Any] | None:
    """loads a YAML file into a dict, will return None if it fails"""

    fileresult = repo.cached_get_file(filename)
    if not fileresult:
        return None
    try:
        filecontents: dict[Any, Any] = YAML(pure=True).load(fileresult.decoded_content.decode("utf-8"))
        return filecontents
    except Exception as error_message:  # noqa: BLE001
        logger.error("Failed to parse yaml file {}: {}", filename, error_message)
        return None
