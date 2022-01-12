""" generic tests """

from github.ContentFile import ContentFile


from .. import RepoLinter

__all__ = [
    "check_files_to_remove",
]

CATEGORY = "generic"


def check_files_to_remove(
    repo: RepoLinter,
) -> None:
    """ check for files to remove """
    contents = repo.repository.get_contents("")
    if isinstance(contents, ContentFile):
        contents = [contents]

    if "files_to_remove" in repo.config:
        for content_file in contents:

            if content_file.name in repo.config["files_to_remove"]:
                repo.error(CATEGORY,
                    f"File '{content_file.name}' needs to be removed from {repo.repository.full_name}.",
                )
