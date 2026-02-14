"""does mkdocs things"""

from difflib import unified_diff
from io import BytesIO
import json
from typing import Tuple

from loguru import logger
from ruyaml import YAML

from github_linter.repolinter import RepoLinter
from github_linter.exceptions import NoChangeNeeded
from github_linter.utils import get_fix_file_path
from github_linter.utils.pages import get_repo_pages_data

CATEGORY = "mkdocs"

LANGUAGES = [
    "all",
]

DEFAULT_CONFIG = {
    "mkdocs_config_files": [
        "docs/mkdocs.yml",
        "mkdocs.yml",
    ],
    "workflow_filepath": ".github/workflows/mkdocs.yml",
}


def needs_mkdocs_workflow(repo: RepoLinter) -> bool:
    """checks that there's a mkdocs config in the repository"""
    for filepath in repo.config[CATEGORY]["mkdocs_config_files"]:
        if repo.cached_get_file(filepath, clear_cache=True):
            return True
    logger.debug("No mkdocs config files found in {}", repo.repository.full_name)
    return False


def check_mkdocs_workflow_exists(repo: RepoLinter) -> None:
    """checks that the mkdocs github actions workflow exists"""
    if needs_mkdocs_workflow(repo):
        if not repo.cached_get_file(repo.config[CATEGORY]["workflow_filepath"], clear_cache=True):
            repo.error(CATEGORY, "MKDocs github actions configuration missing.")
        # TODO: check if the file differs from expected.


def fix_missing_mkdocs_workflow(repo: RepoLinter) -> None:
    """copies the mkdocs workflow if it needs it"""
    if needs_mkdocs_workflow(repo):
        workflow_file = repo.cached_get_file(repo.config[CATEGORY]["workflow_filepath"])
        if workflow_file is None:
            logger.debug("MKDocs workflow file doesn't exist, need to create it.")
            commit_url = repo.create_or_update_file(
                filepath=repo.config[CATEGORY]["workflow_filepath"],
                newfile=get_fix_file_path(CATEGORY, "mkdocs.yml"),
                message="github-linter.mkdocs created MKDocs github actions configuration",
            )
            repo.fix(CATEGORY, f"Created MKDocs github actions configuration: {commit_url}")
        else:
            fix_file = get_fix_file_path(CATEGORY, "mkdocs.yml")

            if workflow_file.decoded_content == fix_file.read_bytes():
                logger.debug("Don't need to update the workflow file!")
                return
            logger.error("Need to update the workflow file")
            commit_url = repo.create_or_update_file(
                filepath=repo.config[CATEGORY]["workflow_filepath"],
                newfile=get_fix_file_path(CATEGORY, "mkdocs.yml"),
                oldfile=workflow_file,
                message="github-linter.mkdocs updated MKDocs github actions configuration",
            )
            repo.fix(CATEGORY, f"Updated MKDocs github actions configuration: {commit_url}")


def generate_expected_config(repo: RepoLinter) -> Tuple[str, bytes]:
    """generates a config file based on the repo"""

    mkdocs_config_file = None
    for filepath in repo.config[CATEGORY]["mkdocs_config_files"]:
        if repo.cached_get_file(filepath) is not None:
            mkdocs_config_file = repo.cached_get_file(filepath)
            mkdocs_filepath = filepath
            continue
    if mkdocs_config_file is None:
        raise FileNotFoundError("No mkdocs config files found.")

    mkdocs_file = YAML(typ="safe").load(mkdocs_config_file.decoded_content)
    logger.debug(json.dumps(mkdocs_file, indent=4, default=str))

    required_fields = {
        "repo_name": repo.repository.full_name,
        "repo_url": repo.repository.html_url,
    }

    if repo.repository.homepage is not None:
        required_fields["site_url"] = repo.repository.homepage
    else:
        pagedata = get_repo_pages_data(repo)
        if pagedata["html_url"] is not None:
            required_fields["site_url"] = pagedata["html_url"]

    for field in required_fields:
        mkdocs_file[field] = required_fields[field]

    writer = BytesIO()
    YAML().dump(mkdocs_file, writer)
    writer.seek(0)
    filecontents = writer.read()
    logger.debug(filecontents)
    return mkdocs_filepath, filecontents


def check_github_metadata(repo: RepoLinter) -> bool:
    """checks that the github metadata fields are set, true = check passes"""

    if not needs_mkdocs_workflow(repo):
        return True

    current_filename, expected_config = generate_expected_config(repo)
    current_file = repo.cached_get_file(current_filename)

    if current_file is None:
        raise ValueError(f"Somehow you got an empty file from {current_filename}, the file may have gone missing while the script was running?")

    if current_file.decoded_content == expected_config:
        logger.debug("Config is up to date, no action required from check_github_metadata")
        return True

    repo.error(CATEGORY, "mkdocs needs updating for github metadata")
    return False


def fix_github_metadata(repo: RepoLinter) -> None:
    """adds github metadata fields which aren't set"""

    if not needs_mkdocs_workflow(repo) or check_github_metadata(repo):
        logger.debug("No change needed")
        raise NoChangeNeeded

    current_filename, expected_config = generate_expected_config(repo)
    current_file = repo.cached_get_file(current_filename)

    if current_file is None or current_file.content is None:
        raise ValueError(f"Somehow you got an empty file from {current_filename}, the file may have gone missing while the script was running?")
    if current_file.decoded_content == expected_config:
        logger.debug("Config is up to date, no action required from fix_github_metadata")
        raise NoChangeNeeded

    # generate a diff for debugging purposes
    diff = unified_diff(
        a=current_file.decoded_content.decode("utf-8").splitlines(),
        b=expected_config.decode("utf-8").splitlines(),
        fromfile=current_filename,
        tofile="updated_file",
    )
    for line in diff:
        logger.debug(line)

    message = f"{CATEGORY} - fix_github_metadata updating {current_filename}"
    try:
        result = repo.create_or_update_file(
            filepath=current_filename,
            newfile=expected_config,
            oldfile=current_file,
            message=message,
        )
        if result is not None:
            repo.fix(CATEGORY, f"{message} - {result}")
    except NoChangeNeeded:
        pass
