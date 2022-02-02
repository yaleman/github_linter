""" test modules """

import sys
from typing import Any, Dict

from loguru import logger

from . import (
    codeowners,
    dependabot,
    generic,
    github_actions,
    homebrew,
    issues,
    mkdocs,
    pylintrc,
    pyproject,
    testing,
    terraform,
)

MODULES = {}
CATEGORY = "tests"
LANGUAGES = ["all"]
DEFAULT_CONFIG: Dict[str, Any] = {}

for module in sys.modules:
    if module.startswith(__name__):
        if hasattr(sys.modules[module], "CATEGORY") and module.startswith(__name__):
            logger.debug("Adding module: {}", module)
            module_name = module.replace(f"{__name__}.", "")
            MODULES[module_name] = sys.modules[module]
        else:
            logger.warning("Module {} doesn't have a CATEGORY attribute.", module)

        if not hasattr(sys.modules[module], "DEFAULT_CONFIG"):
            logger.warning(
                "Module {} doesn't have a DEFAULT_CONFIG attribute, weirdness may occur.",
                module,
            )
        # else:
        # logger.warning("DEFAULT_CONFIG Type: {}", type(sys.modules[module].DEFAULT_CONFIG))

        if not hasattr(sys.modules[module], "LANGUAGES"):
            logger.warning(
                "Module {} doesn't have a LANGUAGES attribute, weirdness may occur.",
                module,
            )
