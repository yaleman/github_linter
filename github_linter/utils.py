""" utility functions """

from json import JSONDecodeError
from typing import Any, Dict, Optional
import os.path
from pathlib import Path
import sys

import json5 as json
from loguru import logger

from .defaults import DEFAULT_LINTER_CONFIG

def get_fix_file_path(category: str, filename: str) -> Path:
    """ gets a Path object for a filename within the fixes dir for the given category """
    module_parent = Path(__file__).parent
    fixes_path = module_parent / f"fixes/{category}/{filename}"
    if not fixes_path.exists():
        base_filename = Path(filename).name
        fixes_path = module_parent / f"fixes/{category}/{base_filename}"
        if not fixes_path.exists():
            logger.error("Fix file {} in category {} not found, bailing.", filename, category)
            sys.exit(1)
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

        if "linter" not in config:
            config["linter"] = {}

        for key in DEFAULT_LINTER_CONFIG:
            if key not in config:
                config[key] = DEFAULT_LINTER_CONFIG[key] # type: ignore

    logger.error("Failed to find config file")
    return {}
