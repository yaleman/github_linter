""" does mkdocs things """

from io import BytesIO

import json

from loguru import logger
from ruyaml import YAML

from github_linter.repolinter import RepoLinter
from github_linter.utils import get_fix_file_path
from github_linter.utils.pages import get_repo_pages_data

CATEGORY = "mkdocs"

LANGUAGES = [
    "all",
]

DEFAULT_CONFIG = {
    "mkdocs_config_files" : [
        "docs/mkdocs.yml",
        "mkdocs.yml",
    ],
    "workflow_filepath" : ".github/workflows/mkdocs.yml"
}


def needs_mkdocs_workflow(repo: RepoLinter) -> bool:
    """ checks that there's a mkdocs config in the repository """
    for filepath in repo.config[CATEGORY]["mkdocs_config_files"]:
        if repo.cached_get_file(filepath, clear_cache=True):
            return True
    return False

def check_mkdocs_workflow_exists(repo: RepoLinter) -> None:
    """ checks that the mkdocs github actions workflow exists """
    if needs_mkdocs_workflow(repo):
        if not repo.cached_get_file(repo.config[CATEGORY]["workflow_filepath"], clear_cache=True):
            repo.error(CATEGORY, "MKDocs github actions configuration missing.")
        # TODO: check if the file differs from expected.

def fix_missing_mkdocs_workflow(repo: RepoLinter) -> None:
    """ copies the mkdocs workflow if it needs it"""
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
            # update it if it's different
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

def check_github_metadata(repo: RepoLinter) -> None:
    """ checks that the github metadata fields are set """

    mkdocs_config_file = None
    for filepath in repo.config[CATEGORY]["mkdocs_config_files"]:
        if repo.cached_get_file(filepath) is not None:
            mkdocs_config_file = repo.cached_get_file(filepath)
            continue
    if mkdocs_config_file is None:
        logger.debug("No mkdocs config files found.")
        return


    mkdocs_file = YAML(typ='safe').load(mkdocs_config_file.decoded_content)
    logger.debug(json.dumps(mkdocs_file, indent=4, default=str))

    pagedata = get_repo_pages_data(repo)
    required_fields = {
        # "site_url": "https://yaleman.github.io/aussiebb/",
        "repo_name": repo.repository.full_name,
        "repo_url": repo.repository.url,
    }


    if pagedata["html_url"] is not None:
        required_fields["site_url"] = pagedata["html_url"]

    # logger.debug("dumping pages data\n{}", json.dumps(pagedata, indent=4))

    # logger.debug(json.dumps(required_fields))
    for field in required_fields:
        mkdocs_file[field] = required_fields[field]
    # logger.debug(json.dumps(mkdocs_file, indent=4, default=str))


    writer = BytesIO()
    YAML().dump(mkdocs_file, writer)
    writer.seek(0)
    logger.debug(writer.read())
    #TODO: turn this into a check/fix
