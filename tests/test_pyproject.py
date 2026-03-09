"""Tests for pyproject module."""

from unittest.mock import Mock

from github_linter.repolinter import RepoLinter
from github_linter.tests.pyproject import check_pyproject_toml, fix_pyproject_readme


def create_mock_pyproject_file() -> Mock:
    """Create a mock pyproject.toml file object."""
    mock_file = Mock()
    mock_file.decoded_content = b"[project]\nname = 'test1'\n"
    mock_file.sha = "deadbeef"
    return mock_file


def create_mock_repo(pyproject: dict, existing_files: set[str] | None = None) -> Mock:
    """Create a mocked RepoLinter for pyproject tests."""
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.config = {"pyproject": {"readme": "README.md"}}
    mock_repo.repository = Mock()
    mock_repo.repository.name = "test1"
    mock_repo.repository.full_name = "testuser/test1"
    pyproject_file = create_mock_pyproject_file()
    files = existing_files or set()

    def cached_get_file(path: str) -> Mock | None:
        if path == "pyproject.toml":
            return pyproject_file
        if path in files:
            mock_file = Mock()
            mock_file.decoded_content = b"file"
            return mock_file
        return None

    mock_repo.load_pyproject.return_value = pyproject
    mock_repo.cached_get_file.side_effect = cached_get_file
    return mock_repo


def test_check_pyproject_toml_accepts_default_readme_path() -> None:
    """No error when the configured readme file exists."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "authors": [], "readme": "README.md"}}, {"README.md"})

    check_pyproject_toml(mock_repo)

    mock_repo.error.assert_not_called()


def test_check_pyproject_toml_accepts_alternate_existing_readme_path() -> None:
    """No error when readme points at another file that exists."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "authors": [], "readme": "docs/README.md"}}, {"docs/README.md"})

    check_pyproject_toml(mock_repo)

    mock_repo.error.assert_not_called()


def test_check_pyproject_toml_errors_when_readme_missing() -> None:
    """Missing readme should be reported."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "authors": []}})

    check_pyproject_toml(mock_repo)

    mock_repo.error.assert_any_call("pyproject", "No 'readme' field in [project] section of config")


def test_check_pyproject_toml_errors_when_readme_file_missing() -> None:
    """Missing readme file target should be reported."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "authors": [], "readme": "docs/README.md"}})

    check_pyproject_toml(mock_repo)

    mock_repo.error.assert_any_call("pyproject", "Readme invalid - file not found: docs/README.md")


def test_check_pyproject_toml_errors_when_readme_not_string() -> None:
    """Non-string readme metadata should be rejected."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "authors": [], "readme": {"file": "README.md"}}})

    check_pyproject_toml(mock_repo)

    mock_repo.error.assert_any_call("pyproject", "Readme invalid - expected a string path, found dict")


def test_fix_pyproject_readme_sets_default_when_missing() -> None:
    """Fix should add the configured readme when absent."""
    mock_repo = create_mock_repo({"project": {"name": "test1"}})
    mock_repo.create_or_update_file.return_value = "https://example.com/commit/1"

    fix_pyproject_readme(mock_repo)

    updated_contents = mock_repo.create_or_update_file.call_args.args[1]
    assert 'readme = "README.md"' in updated_contents
    mock_repo.fix.assert_called_once_with("pyproject", "Updated pyproject.toml readme setting - commit url https://example.com/commit/1")


def test_fix_pyproject_readme_sets_default_when_invalid() -> None:
    """Fix should replace an invalid readme path."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "readme": "missing.md"}})
    mock_repo.create_or_update_file.return_value = "https://example.com/commit/2"

    fix_pyproject_readme(mock_repo)

    updated_contents = mock_repo.create_or_update_file.call_args.args[1]
    assert 'readme = "README.md"' in updated_contents
    mock_repo.fix.assert_called_once_with("pyproject", "Updated pyproject.toml readme setting - commit url https://example.com/commit/2")


def test_fix_pyproject_readme_does_not_write_when_path_is_valid() -> None:
    """Valid existing readme paths should be left alone."""
    mock_repo = create_mock_repo({"project": {"name": "test1", "readme": "docs/README.md"}}, {"docs/README.md"})

    fix_pyproject_readme(mock_repo)

    mock_repo.create_or_update_file.assert_not_called()
    mock_repo.fix.assert_not_called()


def test_fix_pyproject_readme_does_not_create_project_section() -> None:
    """Fix should not invent a project section."""
    mock_repo = create_mock_repo({"tool": {"hatch": {}}})

    fix_pyproject_readme(mock_repo)

    mock_repo.create_or_update_file.assert_not_called()
    mock_repo.fix.assert_not_called()
