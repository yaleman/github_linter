""" utility functions """

from typing import Dict, List, Union
from loguru import logger

from github.GithubException import UnknownObjectException
from github.Repository import Repository
from github.ContentFile import ContentFile

from .types import DICTLIST

def add_result(result_object: DICTLIST, category: str, value: str) -> None:
    """ adds an result to the target object"""
    if category not in result_object:
        result_object[category] = []
    result_object[category].append(value)

def get_file_from_repo(repo_object: Repository, filename: str) -> Union[ContentFile, None]:
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



def check_files_to_remove(
    github_object,
    repo,
    errors_object: Dict[str,List[str]],
    _: Dict[str,List[str]], # warnings_object
    ) -> None:
    """ check for files to remove """
    contents = repo.get_contents("")
    if isinstance(contents, ContentFile):
        contents = [contents]

    for content_file in contents:
        if content_file.name in github_object.config.get("files_to_remove"):
            add_result(
                errors_object,
                "files_to_remove",
                f"File '{content_file.name}' needs to be removed from {repo.full_name}.",
                )
