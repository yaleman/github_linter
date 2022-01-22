""" file loading utility function """

from loguru import logger
import yaml

# TODO: replace this with ruamel.yaml so we only have one cursed dependency

from . import RepoLinter


def load_yaml_file(
    repo: RepoLinter,
    filename: str,
):
    """ loads a YAML file into a dict """

    fileresult = repo.cached_get_file(filename)
    if not fileresult:
        return {}
    try:
        filecontents = yaml.load(
            fileresult.decoded_content.decode("utf-8"),
            Loader=yaml.CLoader,
        )
        return filecontents
    except yaml.YAMLError as exc:
        logger.error("Failed to parse dependabot config: {}", exc)
    return {}
