"""utils for github_actions.dependabot"""

from typing import Optional

import json5 as json
from loguru import logger
from ruyaml import YAML

from ...repolinter import RepoLinter

from .constants import PACKAGE_ECOSYSTEM

from .types import (
    # DefaultConfig,
    DependabotConfigFile,
)


def find_language_in_ecosystem(language: str) -> Optional[str]:
    """checks to see if languages are in VALID_VALUES["package-ecosystem"]"""
    for package in PACKAGE_ECOSYSTEM:
        lowerlang = [lang.lower() for lang in PACKAGE_ECOSYSTEM[package]]
        if language.lower() in lowerlang:
            return package
    return None


def load_dependabot_config_file(
    repo: RepoLinter,
    category: str,
) -> Optional[DependabotConfigFile]:
    """grabs the dependabot config file and loads it"""
    fileresult = repo.cached_get_file(repo.config[category]["config_filename"])
    if not fileresult:
        logger.debug("Couldn't find dependabot config.")
        return None

    try:
        logger.debug("Parsing loaded file into YAML")
        yaml_config = YAML(pure=True).load(fileresult.decoded_content.decode("utf-8"))
        logger.debug("Dumping YAML-> dict file")
        logger.debug(json.dumps(yaml_config, indent=4, default=str, ensure_ascii=False))

        # updates: List[DependabotUpdateConfig] = []
        # if "updates" in yaml_config:
        #     for update in yaml_config["updates"]:
        #         updates.append(DependabotUpdateConfig(**update))
        #     yaml_config["updates"] = updates

        retval = DependabotConfigFile.model_validate(yaml_config)
        logger.debug("dumping DependabotConfigFile")
        logger.debug(json.dumps(retval.model_dump(), indent=4, default=str))
        for update in retval.updates:
            logger.debug("Package: {}", update.package_ecosystem)
        return retval
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to parse dependabot config: {}", exc)
        repo.error(category, f"Failed to parse dependabot config: {exc}")
    return None
