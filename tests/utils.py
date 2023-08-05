""" test utils """

from github.Repository import Repository
from github.Requester import Requester


def generate_test_repo() -> Repository:
    """gets you a test repo"""
    test_requester = Requester(
        auth=None,
        retry=False,
        base_url="https://github.com/yaleman/github_linter/",
        timeout=30,
        pool_size=10,
        per_page=100,
        user_agent="",
        verify=False,
    )

    testrepo = Repository(
        test_requester,
        {},
        attributes={"full_name": "testuser/test1", "name": "test1"},
        completed=True,
    )

    return testrepo
