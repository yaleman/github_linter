""" utility functions """

from json import JSONDecodeError
from typing import Dict, Optional, Any
import os.path
from pathlib import Path

import json5 as json
from loguru import logger

def get_fix_file_path(category: str, filename: str) -> Path:
    """ gets a Path object for a filename within the fixes dir for the given category """
    module_parent = Path(__file__).parent
    fixes_path = module_parent / f"fixes/{category}/{filename}"
    if not fixes_path.exists():
        base_filename = Path(filename).name
        fixes_path = module_parent / f"fixes/{category}/{base_filename}"
    return fixes_path


def load_config() -> Dict[Optional[str],Any]:
    """ loads config """
    for configfile in [
        Path("./github_linter.json"),
        Path(os.path.expanduser("~/.config/github_linter.json")),
    ]:
        if not configfile.exists():
            continue
        try:
            config = json.load(configfile.open(encoding="utf8"))
            logger.debug("Using config file {}", configfile.as_posix())
            return config
        except JSONDecodeError as json_error:
            logger.error("Failed to load {}: {}", configfile.as_posix(), json_error)
    logger.error("Failed to find config file")
    return {}
