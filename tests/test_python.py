"""Tests for the python module"""

from unittest.mock import Mock

from github_linter.repolinter import RepoLinter
from github_linter.tests.python import (
    CATEGORY,
    PLACEHOLDER_TEST_PATH,
    PLACEHOLDER_TEMPLATE_PATH,
    _has_pytest_test,
    check_has_a_pytest_test,
    fix_has_a_pytest_test,
)


def create_tree_entry(path: str, item_type: str = "blob") -> Mock:
    """Create a git tree entry mock."""

    entry = Mock()
    entry.path = path
    entry.type = item_type
    return entry


def create_repo_with_tree(*paths: str) -> Mock:
    """Create a RepoLinter mock with a git tree."""

    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"
    mock_repo.repository.default_branch = "main"
    mock_repo.repository.get_branch.return_value = Mock(commit=Mock(sha="deadbeef"))
    mock_repo.repository.get_git_tree.return_value = Mock(tree=[create_tree_entry(path) for path in paths])
    return mock_repo


def test_has_pytest_test_matches_top_level_test_file() -> None:
    """A tests/test*.py file should satisfy the check."""

    mock_repo = create_repo_with_tree("tests/test_example.py")

    assert _has_pytest_test(mock_repo)


def test_has_pytest_test_matches_nested_test_file() -> None:
    """Nested tests should also satisfy the check."""

    mock_repo = create_repo_with_tree("tests/unit/test_example.py")

    assert _has_pytest_test(mock_repo)


def test_has_pytest_test_rejects_non_matching_paths() -> None:
    """Non-test files should not satisfy the check."""

    mock_repo = create_repo_with_tree("tests/example.py", "src/test_example.py", "tests/test_example.txt")

    assert not _has_pytest_test(mock_repo)


def test_check_has_a_pytest_test_reports_missing_tests() -> None:
    """The check should report an error when no pytest tests exist."""

    mock_repo = create_repo_with_tree("README.md", "src/app.py")

    check_has_a_pytest_test(mock_repo)

    mock_repo.error.assert_called_once_with(CATEGORY, "Missing pytest tests. Expected at least one Python file matching tests/test*.py.")


def test_check_has_a_pytest_test_accepts_existing_test() -> None:
    """The check should not report errors when a test exists."""

    mock_repo = create_repo_with_tree("tests/test_example.py")

    check_has_a_pytest_test(mock_repo)

    mock_repo.error.assert_not_called()


def test_fix_has_a_pytest_test_creates_placeholder() -> None:
    """The fix should create a placeholder test file when none exist."""

    mock_repo = create_repo_with_tree("README.md", "src/app.py")
    mock_repo.create_or_update_file.return_value = "https://example.com/commit"

    fix_has_a_pytest_test(mock_repo)

    mock_repo.create_or_update_file.assert_called_once()
    create_call = mock_repo.create_or_update_file.call_args.kwargs
    assert create_call["filepath"] == PLACEHOLDER_TEST_PATH
    assert str(create_call["newfile"]).endswith(f"github_linter/fixes/python/{PLACEHOLDER_TEMPLATE_PATH}")
    assert create_call["oldfile"] is None
    mock_repo.fix.assert_called_once_with(CATEGORY, "Created placeholder pytest test: https://example.com/commit")


def test_fix_has_a_pytest_test_skips_when_test_exists() -> None:
    """The fix should do nothing when pytest tests already exist."""

    mock_repo = create_repo_with_tree("tests/test_example.py")

    fix_has_a_pytest_test(mock_repo)

    mock_repo.create_or_update_file.assert_not_called()
    mock_repo.fix.assert_not_called()
