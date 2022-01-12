""" test modules """

import sys

from loguru import logger

from . import dependabot, generic, github_actions, \
    issues, \
    pylintrc, pyproject, \
    testing, \
    terraform

MODULES = {}

for module in sys.modules:
    if hasattr(sys.modules[module], "CATEGORY") and module.startswith(__name__):
        logger.debug("Adding module: {}", module)
        module_name = module.replace(f"{__name__}.", "")
        MODULES[module_name] = sys.modules[module]
