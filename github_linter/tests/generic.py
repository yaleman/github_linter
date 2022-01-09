""" generic tests """

from github.ContentFile import ContentFile


from .. import GithubLinter
from ..types import DICTLIST
from ..utils import add_result

__all__ = [
    "check_files_to_remove",
]

CATEGORY = "generic"


def check_files_to_remove(
    github_object: GithubLinter,
    repo,
    errors_object: DICTLIST,
    _: DICTLIST,  # warnings_object
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
