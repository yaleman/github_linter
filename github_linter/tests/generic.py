""" generic tests """

from typing import List, TypedDict

from github.ContentFile import ContentFile

from .. import RepoLinter

__all__ = [
    "check_files_to_remove",
]
LANGUAGES = [
    "all",
]
CATEGORY = "generic"
class DefaultConfig(TypedDict):
    """ config object """
    files_to_remove: List[str]

DEFAULT_CONFIG: DefaultConfig = {
    "files_to_remove" : [
        "Pipfile",
        "Pipfile.lock",
        ".DS_Store",
        ".drone.yml",
        "setup.py",
        "distutils.cfg",
    ]
}

def check_files_to_remove(
    repo: RepoLinter,
) -> None:
    """ check for files to remove """
    contents = repo.repository.get_contents("")
    if isinstance(contents, ContentFile):
        contents = [contents]

    for content_file in contents:
        if content_file.name in repo.config[CATEGORY]["files_to_remove"]:
            repo.error(CATEGORY,
                f"File '{content_file.name}' needs to be removed from {repo.repository.full_name}.",
            )
