"""test modules"""

import sys
from types import ModuleType
from typing import Any, Dict, List, Optional

from loguru import logger  # type: ignore


from . import (
    codeowners,  # noqa: F401
    dependabot,  # noqa: F401
    docs,  # noqa: F401
    generic,  # noqa: F401
    github_actions,  # noqa: F401
    homebrew,  # noqa: F401
    issues,  # noqa: F401
    mkdocs,  # noqa: F401
    # pylintrc,
    pyproject,  # noqa: F401
    security_md,  # noqa: F401
    terraform,  # noqa: F401
)

CATEGORY = "tests"
LANGUAGES = ["all"]
DEFAULT_CONFIG: Dict[str, Any] = {}


def load_modules(module_allowlist: Optional[List[str]] = None) -> Dict[str, ModuleType]:
    """loads the modules"""
    module_list: Dict[str, Any] = {}

    for module in sys.modules:
        if module.startswith(__name__) and len(module.split(".")) == 3:
            # skip them if we're filtering by module
            if module_allowlist and module not in module_allowlist:
                continue

            if hasattr(sys.modules[module], "CATEGORY") and module.startswith(__name__):
                # logger.debug("Adding module: {}", module)
                module_name = module.replace(f"{__name__}.", "")
                module_list[module_name] = sys.modules[module]
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
    return module_list


MODULES = load_modules()
