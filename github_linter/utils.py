""" utility functions """

from typing import Union

from loguru import logger

from github.GithubException import UnknownObjectException
from github.Repository import Repository
from github.ContentFile import ContentFile

from .types import DICTLIST


def add_result(result_object: DICTLIST, category: str, value: str) -> None:
    """ adds an result to the target object"""
    if category not in result_object:
        result_object[category] = []
    if value not in result_object[category]:
        result_object[category].append(value)
    logger.debug("{} - {}", category, value)


def get_file_from_repo(
    repo_object: Repository, filename: str
) -> Union[ContentFile, None]:
    """ looks for a file or returns none"""
    try:
        fileresult = repo_object.get_contents(filename)
        if not fileresult:
            logger.debug("Couldn't find {}...?", filename)
            return None
        if isinstance(fileresult, list):
            fileresult = fileresult[0]
        return fileresult
    except UnknownObjectException:
        logger.debug("{} not found in {}", filename, repo_object.full_name)
    return None
