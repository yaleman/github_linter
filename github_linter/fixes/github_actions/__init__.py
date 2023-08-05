""" github-actions programmatic fixes """
import json

from loguru import logger
from pydantic import BaseModel
from requests import Response
from github_linter.repolinter import RepoLinter

__all__ = [
    "get_repo_default_workflow_permissions",
    "set_repo_default_workflow_permissions",
    "VALID_DEFAULT_WORKFLOW_PERMISSIONS",
]

VALID_DEFAULT_WORKFLOW_PERMISSIONS = ["read", "write"]


class WorkflowPermissions(BaseModel):
    """workflow permissions"""

    default_workflow_permissions: str
    can_approve_pull_request_reviews: bool


def get_repo_default_workflow_permissions(
    repo: RepoLinter,
) -> WorkflowPermissions:
    """Get the default permissions for the repository's workflows"""

    # https://docs.github.com/en/rest/actions/permissions?apiVersion=2022-11-28#set-default-workflow-permissions-for-a-repository

    # pylint: disable=protected-access
    resp = repo.repository3._get(
        f"https://api.github.com/repos/{repo.repository3.owner}/{repo.repository3.name}/actions/permissions/workflow",
    )
    try:
        logger.debug(resp.json())
    except json.JSONDecodeError:
        logger.debug(resp.text)
    return WorkflowPermissions(**resp.json())


def set_repo_default_workflow_permissions(
    repo: RepoLinter,
    default_workflow_permissions: str,
    can_approve_pull_request_reviews: bool,
) -> bool:
    """Set the default permissions for the repository's workflows"""

    # https://docs.github.com/en/rest/actions/permissions?apiVersion=2022-11-28#set-default-workflow-permissions-for-a-repository

    if default_workflow_permissions not in VALID_DEFAULT_WORKFLOW_PERMISSIONS:
        raise ValueError(
            f"Invalid default_workflow_permissions: {default_workflow_permissions}. Valid values are: {VALID_DEFAULT_WORKFLOW_PERMISSIONS}"
        )

    payload = {
        "default_workflow_permissions": default_workflow_permissions,
        "can_approve_pull_request_reviews": can_approve_pull_request_reviews,
    }

    # pylint: disable=protected-access
    res: Response = repo.repository3._put(
        f"https://api.github.com/repos/{repo.repository3.owner}/{repo.repository3.name}/actions/permissions/workflow",
        data=json.dumps(payload),
    )
    try:
        logger.debug(res.json())
    except json.JSONDecodeError:
        logger.debug(res.text)

    result: bool = res.status_code == 204
    return result
    # logger.debug(res)
