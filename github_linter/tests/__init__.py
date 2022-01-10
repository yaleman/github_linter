""" test modules """

from . import generic, dependabot, issues, pylintrc, pyproject, testing

MODULES = {
    "dependabot": dependabot,
    "generic": generic,
    "issues": issues,
    "pylintrc": pylintrc,
    "pyproject": pyproject,
    "testing" : testing,
}
