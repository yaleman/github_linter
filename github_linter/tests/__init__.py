""" test modules """

import sys
from typing import Any, Dict

from loguru import logger

from . import (
    codeowners,
    dependabot,
    docs,
    generic,
    github_actions,
    homebrew,
    issues,
    mkdocs,
    pylintrc,
    pyproject,
    security_md,
    testing,
    terraform,
)

MODULES = {}
CATEGORY = "tests"
LANGUAGES = ["all"]
DEFAULT_CONFIG: Dict[str, Any] = {}

for module in sys.modules:
    if module.startswith(__name__) and len(module.split(".")) == 3:
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
        if not hasattr(sys.modules[module], "LANGUAGES"):
            logger.warning(
                "Module {} doesn't have a LANGUAGES attribute, weirdness may occur.",
                module,
            )
