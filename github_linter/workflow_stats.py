"""pulls stats on workflow runs and returns them in a parseable way"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
from loguru import logger
from pydantic import BaseModel

from github_linter import GithubLinter


class Actor(BaseModel):
    login: str
    id: int
    node_id: str
    avatar_url: str | None
    gravatar_id: str | None
    url: str | None
    html_url: str | None
    followers_url: str | None
    following_url: str | None
    gists_url: str | None
    starred_url: str | None
    subscriptions_url: str | None
    organizations_url: str | None
    repos_url: str | None
    events_url: str | None
    received_events_url: str | None
    type: str
    site_admin: bool

    def drop_urls(self) -> None:
        """remove all the URLs from things for brevity"""
        for field in dir(self):
            if field.endswith("_url"):
                setattr(self, field, None)
        self.url = None


class Repository(BaseModel):
    owner: Actor

    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    description: str
    fork: bool
    html_url: str | None
    url: str | None
    forks_url: str | None
    keys_url: str | None
    collaborators_url: str | None
    teams_url: str | None
    hooks_url: str | None
    issue_events_url: str | None
    events_url: str | None
    assignees_url: str | None
    branches_url: str | None
    tags_url: str | None
    blobs_url: str | None
    git_tags_url: str | None
    git_refs_url: str | None
    trees_url: str | None
    statuses_url: str | None
    languages_url: str | None
    stargazers_url: str | None
    contributors_url: str | None
    subscribers_url: str | None
    subscription_url: str | None
    commits_url: str | None
    git_commits_url: str | None
    comments_url: str | None
    issue_comment_url: str | None
    contents_url: str | None
    compare_url: str | None
    merges_url: str | None
    archive_url: str | None
    downloads_url: str | None
    issues_url: str | None
    pulls_url: str | None
    milestones_url: str | None
    notifications_url: str | None
    labels_url: str | None
    releases_url: str | None
    deployments_url: str | None

    def drop_urls(self) -> None:
        """remove all the URLs from things for brevity"""
        for field in dir(self):
            if field.endswith("_url"):
                setattr(self, field, None)
        self.owner.drop_urls()
        self.url = None


class RunData(BaseModel):
    """individual run response in the workflowruns object"""

    actor: Actor
    repository: Repository
    head_repository: Repository | None

    id: int
    name: str
    node_id: str
    head_branch: str
    head_sha: str
    path: str
    display_title: str
    run_number: int
    event: str
    status: str
    conclusion: str | None
    workflow_id: int
    check_suite_id: int
    check_suite_node_id: str
    url: str | None
    html_url: str | None
    pull_requests: list[Any]
    triggering_actor: Actor | None
    created_at: datetime
    updated_at: datetime | None
    run_attempt: int
    referenced_workflows: list[Any]
    run_started_at: datetime | None
    jobs_url: str | None
    logs_url: str | None
    check_suite_url: str | None
    artifacts_url: str | None
    cancel_url: str | None
    rerun_url: str | None
    previous_attempt_url: str | None
    workflow_url: str | None
    runtime: timedelta | None = None

    def calculate_runtime(self) -> timedelta | None:
        """calculates and updates the runtime if possible"""

        if self.updated_at is None:
            return None
        self.runtime = self.updated_at - self.created_at
        return self.runtime

    def drop_urls(self) -> None:
        """remove all the URLs from things for brevity"""
        for field in dir(self):
            if field.endswith("_url"):
                logger.debug("Dropping field {}", field)
                setattr(self, field, None)

        if self.actor is not None:
            self.actor.drop_urls()
        if self.repository is not None:
            self.repository.drop_urls()
        if self.head_repository is not None:
            self.head_repository.drop_urls()
        if self.triggering_actor is not None:
            self.triggering_actor.drop_urls()


class WorkflowRuns(BaseModel):
    """basic response"""

    total_count: int
    workflow_runs: list[RunData]

    def has_more_runs(self) -> bool:
        """ave we more runs than were returned?"""
        return self.total_count > len(self.workflow_runs)


status_log_map = {
    "completed": logger.success,
    "in_progress": logger.info,
    "queued": logger.warning,
    "action_required": logger.info,
    "cancelled": logger.warning,
    "failure": logger.error,
    "neutral": logger.info,
    "skipped": logger.info,
    "stale": logger.info,
    "success": logger.info,
    "timed_out": logger.error,
    "requested": logger.info,
    "waiting": logger.info,
    "pending": logger.info,
}


def parse_file(filename: str) -> None:
    """parse a file and check things"""
    with Path(filename).open(encoding="utf-8") as file_handle:
        for line in file_handle:
            run = RunData.model_validate_json(line)
            run.calculate_runtime()
            log_action = status_log_map.get(run.conclusion, logger.info)
            run_conclusion = run.conclusion if run.conclusion is not None else "<unknown conclusion>"
            log_action(
                "{}\t{}{}\t{}\t{}",
                run.id,
                run_conclusion,
                f"\t(in {run.runtime})" if run.runtime is not None else "",
                run.head_branch,
                run.name,
            )


@click.command()
@click.option("-o", "--owner")
@click.option("-r", "--repo")
@click.option("-f", "--fullname", help="Full name of the repo, e.g. owner/repo")
@click.option(
    "-e",
    "--earliest",
    help="Earliest date-stamp to query. Ref: <https://docs.github.com/en/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax#query-for-dates>",
)
@click.option("-F", "--filename", help="Output filename, otherwise it'll return to stdout")
@click.option("-p", "--parse", help="Parse existing run file", is_flag=True, default=False)
def main(
    owner: str | None = None,
    repo: str | None = None,
    fullname: str | None = None,
    filename: str | None = None,
    earliest: str | None = None,
    parse: bool = False,
) -> None:
    """Main function"""
    logger.configure(
        handlers=[
            {"sink": sys.stderr, "format": "<level>{message}</level>"},
        ],
        extra={"common_to_all": "default"},
        # activation=[("my_module.secret", False), ("another_library.module", True)],
    )

    if parse:
        if filename is None:
            logger.error("Specify a filename to parse!")
            return
        return parse_file(filename)

    if fullname is not None:
        owner, repo = fullname.split("/")
    else:
        if owner is None or repo is None:
            logger.error("Specify either fullname or owner and repo")
            return
        fullname = f"{owner}/{repo}"

    linter = GithubLinter()

    params = None
    if earliest is not None:
        params = {
            "created": f">{earliest}",
        }
    try:
        url = linter.github3.session.build_url(f"repos/{owner}/{repo}/actions/runs")
        response = linter.github3._get(url, params=params)
    except Exception as error:  # noqa: BLE001
        logger.error(f"Failed to query workflow runs: {error}")
        return

    runs = WorkflowRuns.model_validate(response.json())
    if not runs.workflow_runs:
        logger.error("No runs found!")
        return

    for run in runs.workflow_runs:
        run.calculate_runtime()
        run.drop_urls()

    if filename is not None:
        logger.debug("Writing to {}", filename)
        with Path(filename).open(mode="w", encoding="utf-8") as fh:
            for run in runs.workflow_runs:
                fh.write(run.model_dump_json() + "\n")
    else:
        for run in runs.workflow_runs:
            print(run.model_dump_json(exclude_none=True))


if __name__ == "__main__":
    main()
