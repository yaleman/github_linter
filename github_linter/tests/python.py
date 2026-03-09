"""Python-specific checks and fixes"""

from pathlib import PurePosixPath

from github.GithubException import GithubException
from loguru import logger

from ..repolinter import RepoLinter
from ..utils import get_fix_file_path

CATEGORY = "python"
LANGUAGES = ["python"]
DEFAULT_CONFIG = {}

PLACEHOLDER_TEST_PATH = "tests/test_nothing.py"
PLACEHOLDER_TEMPLATE_PATH = "placeholder_test_nothing.py"


def _is_pytest_test_path(path: str) -> bool:
    """Return True when the path is a pytest-style test under tests/."""

    path_parts = PurePosixPath(path).parts
    if not path_parts or path_parts[0] != "tests":
        return False

    filename = path_parts[-1]
    return filename.startswith("test") and filename.endswith(".py")


def _has_pytest_test(repo: RepoLinter) -> bool:
    """Check the repository tree for at least one pytest-style test file."""

    default_branch = repo.repository.get_branch(repo.repository.default_branch)
    tree = repo.repository.get_git_tree(default_branch.commit.sha, recursive=True)

    for tree_item in tree.tree:
        if getattr(tree_item, "type", None) != "blob":
            continue
        if _is_pytest_test_path(getattr(tree_item, "path", "")):
            return True

    return False


def check_has_a_pytest_test(repo: RepoLinter) -> None:
    """Ensure Python repositories contain at least one pytest-style test file."""

    repo.skip_on_archived()

    try:
        if _has_pytest_test(repo):
            return
    except GithubException as exc:
        logger.error("Failed to inspect repository tree for {}: {}", repo.repository.full_name, exc)
        repo.error(CATEGORY, "Failed to inspect repository tree for pytest tests.")
        return

    repo.error(CATEGORY, "Missing pytest tests. Expected at least one Python file matching tests/test*.py.")


def fix_has_a_pytest_test(repo: RepoLinter) -> None:
    """Create a placeholder pytest file when the repository has no tests."""

    repo.skip_on_archived()

    try:
        if _has_pytest_test(repo):
            return
    except GithubException as exc:
        logger.error("Failed to inspect repository tree for {}: {}", repo.repository.full_name, exc)
        repo.error(CATEGORY, "Failed to inspect repository tree for pytest tests.")
        return

    placeholder_file = get_fix_file_path(CATEGORY, PLACEHOLDER_TEMPLATE_PATH)
    commit_url = repo.create_or_update_file(
        filepath=PLACEHOLDER_TEST_PATH,
        newfile=placeholder_file,
        oldfile=None,
        message="github_linter: add placeholder pytest test",
    )

    if commit_url:
        repo.fix(CATEGORY, f"Created placeholder pytest test: {commit_url}")
    else:
        repo.error(CATEGORY, "Failed to create placeholder pytest test.")
