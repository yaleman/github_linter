"""helper to pull pages information"""

import json
from typing import TypedDict

from loguru import logger

from .. import GithubLinter
from ..repolinter import RepoLinter


class PagesSource(TypedDict):
    """subclass of PagesData"""

    branch: str | None
    path: str | None


class PagesData(TypedDict):
    """returend from a call to /repos/{repo}/{owner}/pages"""

    url: str | None
    status: str | None
    cname: str | None
    custom_404: bool
    html_url: str | None
    source: PagesSource
    public: bool
    protected_domain_state: str | None
    pending_domain_unverified_at: str | None
    https_enforced: str | None


def get_repo_pages_data(repo: RepoLinter) -> PagesData:
    """gets the repo's pages information

    documenation here: https://docs.github.com/en/rest/reference/pages
    """
    github = GithubLinter()
    github.do_login()
    url = f"/repos/{repo.repository.full_name}/pages"
    requester = getattr(github.github, "_Github__requester", None)
    if requester is None:
        raise ValueError("Github object doesn't have a requester, can't get pages data.")
    pagesdata = requester.requestJson(verb="GET", url=url)

    if len(pagesdata) != 3:
        raise ValueError(f"Got {len(pagesdata)} from requesting the repo pages endpoint ({url}).")

    pages: PagesData = json.loads(pagesdata[2])
    if pages is None:
        raise ValueError(f"Invalid data returned from requesting the repo pages endpoint ({url}).")

    logger.debug(
        json.dumps(
            pages,
            indent=4,
            default=str,
        )
    )

    return pages
