""" checks for dependabot config """

# import json
# from typing import Dict, List


# from loguru import logger
from github.Repository import Repository

# import yaml

from github_linter import GithubLinter

# from . import GithubLinter
from ..types import DICTLIST
from ..utils import add_result, get_file_from_repo

CATEGORY = "pylintrc"


def check_pylintrc(
    _: GithubLinter,
    repo: Repository,
    __: DICTLIST,  #
    warnings_object: DICTLIST,
):
    """ checks for .pylintrc config """

    pylintrc = get_file_from_repo(repo, ".pylintrc")

    if not pylintrc:
        add_result(warnings_object, CATEGORY, ".pylintrc not found")
