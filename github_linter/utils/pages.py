"""helper to pull pages information"""

import json

from typing import Optional, TypedDict

from loguru import logger

from ..repolinter import RepoLinter
from .. import GithubLinter


class PagesSource(TypedDict):
    """subclass of PagesData"""

    branch: Optional[str]
    path: Optional[str]


class PagesData(TypedDict):
    """returend from a call to /repos/{repo}/{owner}/pages"""

    url: Optional[str]
    status: Optional[str]
    cname: Optional[str]
    custom_404: bool
    html_url: Optional[str]
    source: PagesSource
    public: bool
    protected_domain_state: Optional[str]
    pending_domain_unverified_at: Optional[str]
    https_enforced: Optional[str]


def get_repo_pages_data(repo: RepoLinter) -> PagesData:
    """gets the repo's pages information

    documenation here: https://docs.github.com/en/rest/reference/pages
    """
    github = GithubLinter()
    github.do_login()
    url = f"/repos/{repo.repository.full_name}/pages"
    if hasattr(github.github, "_Github__requester") and github.github._Github__requester is not None:
        pagesdata = github.github._Github__requester.requestJson(verb="GET", url=url)  # type: ignore[possibly-missing-attribute]
    else:
        raise ValueError("Github object doesn't have a requester, can't get pages data.")

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
