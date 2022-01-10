""" test modules """

from . import generic, dependabot, issues, pylintrc, pyproject

MODULES = {
    "dependabot": dependabot,
    "generic": generic,
    "issues": issues,
    "pylintrc": pylintrc,
    "pyproject": pyproject,
}
