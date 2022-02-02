""" generic tests """

from io import StringIO

from typing import Any, Dict, List, Optional, TypedDict, Union

from loguru import logger
import ruamel.yaml  # type: ignore

from github.ContentFile import ContentFile

from .. import RepoLinter

__all__ = [
    "check_files_to_remove",
]
LANGUAGES = [
    "all",
]
CATEGORY = "generic"

OptionalListOrStr = Optional[Union[List[str], str]]


class FundingDict(TypedDict):
    """typing object for the funding section
    based on https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/displaying-a-sponsor-button-in-your-repository"""

    community_bridge: Optional[str]
    custom: OptionalListOrStr
    github: OptionalListOrStr
    issuehunt: Optional[str]
    ko_fi: Optional[str]
    liberapay: Optional[str]
    open_collective: Optional[str]
    otechie: Optional[str]
    patreon: Optional[str]
    tidelift: Optional[str]


class DefaultConfig(TypedDict):
    """ config object """

    files_to_remove: List[str]
    funding: FundingDict


DEFAULT_CONFIG: DefaultConfig = {
    "files_to_remove": [
        "Pipfile",
        "Pipfile.lock",
        ".DS_Store",
        ".drone.yml",
        "setup.py",
        "distutils.cfg",
    ],
    "funding": {
        "community_bridge": None,
        "custom": None,
        "github": None,
        "issuehunt": None,
        "ko_fi": None,
        "liberapay": None,
        "open_collective": None,
        "otechie": None,
        "patreon": None,
        "tidelift": None,
    },
}


def parse_funding_file(input_string: Union[str, bytes]) -> FundingDict:
    """ parses the FUNDING.yml file into a FundingDict """
    parsed_data: FundingDict = ruamel.yaml.YAML(pure=True).load(input_string)
    return parsed_data


def generate_funding_file(input_data: Dict[str, Any]):
    """ generates a bytes object of a funding file based on a FundingDict """
    output_data = {}

    for key in input_data.keys():
        if input_data[key] is not None:
            output_data[key] = input_data[key]

    yaml = ruamel.yaml.YAML(pure=True)
    yaml.brace_single_entry_mapping_in_flow_sequence = True
    # yaml.default_flow_style = False
    outputio = StringIO()

    yaml.dump(output_data, outputio)
    outputio.seek(0)

    # pylint: disable=line-too-long
    # doc_line = "# Documentation for this file format is here: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/displaying-a-sponsor-button-in-your-repository"
    result = outputio.read()
    return result


def check_files_to_remove(
    repo: RepoLinter,
) -> None:
    """ check for files to remove """
    contents = repo.repository.get_contents("")
    if isinstance(contents, ContentFile):
        contents = [contents]

    for content_file in contents:
        if content_file.name in repo.config[CATEGORY]["files_to_remove"]:
            repo.error(
                CATEGORY,
                f"File '{content_file.name}' needs to be removed from {repo.repository.full_name}.",
            )


def fix_funding_file(repo: RepoLinter) -> None:
    """ updates the funding file """

    filename = ".github/FUNDING.yml"
    expected_file = generate_funding_file(repo.config[CATEGORY]["funding"])
    print(expected_file)

    filecontents = repo.cached_get_file(filename)
    if filecontents and expected_file == filecontents.decoded_content.decode("utf-8"):
        logger.debug("Don't need to update {}, already good.", filename)
        return

    result = repo.create_or_update_file(filename, expected_file, oldfile=filecontents)
    if result:
        repo.fix(CATEGORY, f"Updated .github/FUNDING.yml file, commit URL {result}")
    else:
        repo.error(CATEGORY, "Failed to update .github/FUNDING.yml file.")
