""" pulls stats on workflow runs and returns them in a parseable way """

from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, List, Optional
import click
from loguru import logger
from pydantic import BaseModel

from github_linter import GithubLinter


class Actor(BaseModel):
    login: str
    id: int
    node_id: str
    avatar_url: Optional[str]
    gravatar_id: Optional[str]
    url: Optional[str]
    html_url: Optional[str]
    followers_url: Optional[str]
    following_url: Optional[str]
    gists_url: Optional[str]
    starred_url: Optional[str]
    subscriptions_url: Optional[str]
    organizations_url: Optional[str]
    repos_url: Optional[str]
    events_url: Optional[str]
    received_events_url: Optional[str]
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
    html_url: Optional[str]
    url: Optional[str]
    forks_url: Optional[str]
    keys_url: Optional[str]
    collaborators_url: Optional[str]
    teams_url: Optional[str]
    hooks_url: Optional[str]
    issue_events_url: Optional[str]
    events_url: Optional[str]
    assignees_url: Optional[str]
    branches_url: Optional[str]
    tags_url: Optional[str]
    blobs_url: Optional[str]
    git_tags_url: Optional[str]
    git_refs_url: Optional[str]
    trees_url: Optional[str]
    statuses_url: Optional[str]
    languages_url: Optional[str]
    stargazers_url: Optional[str]
    contributors_url: Optional[str]
    subscribers_url: Optional[str]
    subscription_url: Optional[str]
    commits_url: Optional[str]
    git_commits_url: Optional[str]
    comments_url: Optional[str]
    issue_comment_url: Optional[str]
    contents_url: Optional[str]
    compare_url: Optional[str]
    merges_url: Optional[str]
    archive_url: Optional[str]
    downloads_url: Optional[str]
    issues_url: Optional[str]
    pulls_url: Optional[str]
    milestones_url: Optional[str]
    notifications_url: Optional[str]
    labels_url: Optional[str]
    releases_url: Optional[str]
    deployments_url: Optional[str]

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
    head_repository: Optional[Repository]

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
    conclusion: Optional[str]
    workflow_id: int
    check_suite_id: int
    check_suite_node_id: str
    url: Optional[str]
    html_url: Optional[str]
    pull_requests: List[Any]
    triggering_actor: Optional[Actor]
    created_at: datetime
    updated_at: Optional[datetime]
    run_attempt: int
    referenced_workflows: List[Any]
    run_started_at: Optional[datetime]
    jobs_url: Optional[str]
    logs_url: Optional[str]
    check_suite_url: Optional[str]
    artifacts_url: Optional[str]
    cancel_url: Optional[str]
    rerun_url: Optional[str]
    previous_attempt_url: Optional[str]
    workflow_url: Optional[str]
    runtime: Optional[timedelta] = None

    def calculate_runtime(self) -> Optional[timedelta]:
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
    workflow_runs: List[RunData]

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
    for line in Path(filename).open(encoding="utf-8").readlines():
        run = RunData.model_validate_json(line)
        run.calculate_runtime()
        if run.conclusion in status_log_map:
            log_action = status_log_map[run.conclusion]
        else:
            log_action = logger.info
        run_conclusion = (
            run.conclusion if run.conclusion is not None else "<unknown conclusion>"
        )
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
@click.option(
    "-F", "--filename", help="Output filename, otherwise it'll return to stdout"
)
@click.option(
    "-p", "--parse", help="Parse existing run file", is_flag=True, default=False
)
def main(
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    fullname: Optional[str] = None,
    filename: Optional[str] = None,
    earliest: Optional[str] = None,
    parse: bool = False,
) -> None:
    """Main function"""
    logger.configure(
        handlers=[
            dict(sink=sys.stderr, format="<level>{message}</level>"),
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
    except Exception as error:
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
