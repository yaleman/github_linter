""" GithubLinter Exceptions """

from loguru import logger

__all__ = [
    "NoChangeNeeded",
    "SkipOnArchived",
]

class SkipOnArchived(Exception):
    """ skip a test if the repo's archived """

    def __init__(self, *args: object) -> None:
        """ adds a logging step """
        logger.debug("Skipping Archived Repo")
        super().__init__(*args)

class NoChangeNeeded(Exception):
    """ skip a fix if there's no change required """

    def __init__(self, *args: object) -> None:
        """ adds a logging step """
        logger.debug("Fix not required, skipping.")
        super().__init__(*args)
