""" generic tests """

from github.ContentFile import ContentFile


from .. import GithubLinter
from ..exceptions import RepositoryNotSet
from ..types import DICTLIST
from ..utils import add_result

__all__ = [
    "check_files_to_remove",
]

CATEGORY = "generic"


def check_files_to_remove(
    github_object: GithubLinter,
    errors_object: DICTLIST,
    _: DICTLIST,  # warnings_object
) -> None:
    """ check for files to remove """
    if not github_object.current_repo:
        raise RepositoryNotSet
    contents = github_object.current_repo.get_contents("")
    if isinstance(contents, ContentFile):
        contents = [contents]

    for content_file in contents:
        if content_file.name in github_object.config.get("files_to_remove"):
            add_result(
                errors_object,
                CATEGORY,
                f"File '{content_file.name}' needs to be removed from {github_object.current_repo.full_name}.",
            )
