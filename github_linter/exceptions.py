""" GithubLinter Exceptions """

from loguru import logger

class SkipOnArchived(Exception):
    """ skip a test if the repo's archived """

    def __init__(self, *args):
        """ adds a logging step """
        logger.debug("Skipping Archived Repo")
        super().__init__(*args)
