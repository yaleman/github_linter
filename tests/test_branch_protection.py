"""Tests for branch protection module"""

from typing import List
from unittest.mock import Mock

from github_linter.repolinter import RepoLinter
from github_linter.tests.branch_protection import (
    _get_available_checks_for_repo,
    _validate_required_checks,
)


def create_mock_workflow_file(name: str, content: str) -> Mock:
    """Create a mock workflow file ContentFile object"""
    mock_file = Mock()
    mock_file.name = name
    mock_file.decoded_content = content.encode('utf-8')
    return mock_file


def test_get_available_checks_with_simple_workflow() -> None:
    """Test parsing a simple workflow file with jobs"""

    workflow_content = """
name: Test Workflow
on: [push, pull_request]

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()

    # Mock get_contents to return our test workflow
    workflow_files = [
        create_mock_workflow_file("test.yml", workflow_content)
    ]
    mock_repo.repository.get_contents.return_value = workflow_files

    # Call the function
    available_checks = _get_available_checks_for_repo(mock_repo)

    # Verify results
    assert "pytest" in available_checks
    assert "mypy" in available_checks
    assert "ruff" in available_checks
    assert len(available_checks) == 3


def test_get_available_checks_with_multiple_workflows() -> None:
    """Test parsing multiple workflow files"""

    workflow1 = """
name: Python Tests
jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - run: pytest
"""

    workflow2 = """
name: Linting
jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check

  mypy:
    runs-on: ubuntu-latest
    steps:
      - run: mypy
"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()

    # Mock get_contents to return multiple workflow files
    workflow_files = [
        create_mock_workflow_file("test.yml", workflow1),
        create_mock_workflow_file("lint.yaml", workflow2),
    ]
    mock_repo.repository.get_contents.return_value = workflow_files

    # Call the function
    available_checks = _get_available_checks_for_repo(mock_repo)

    # Verify results
    assert "pytest" in available_checks
    assert "mypy" in available_checks
    assert "ruff" in available_checks
    assert len(available_checks) == 3


def test_get_available_checks_with_no_workflows() -> None:
    """Test when .github/workflows directory doesn't exist"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"

    # Mock get_contents to raise UnknownObjectException
    from github.GithubException import UnknownObjectException
    mock_repo.repository.get_contents.side_effect = UnknownObjectException(
        status=404,
        data={"message": "Not Found"},
        headers={}
    )

    # Call the function
    available_checks = _get_available_checks_for_repo(mock_repo)

    # Should return empty set
    assert len(available_checks) == 0


def test_get_available_checks_with_invalid_yaml() -> None:
    """Test handling of invalid YAML in workflow files"""

    invalid_yaml = """
name: Invalid
jobs:
  test:
    this is not valid yaml: [[[
"""

    valid_yaml = """
name: Valid
jobs:
  pytest:
    runs-on: ubuntu-latest
"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"

    # Mock get_contents with one invalid and one valid workflow
    workflow_files = [
        create_mock_workflow_file("invalid.yml", invalid_yaml),
        create_mock_workflow_file("valid.yml", valid_yaml),
    ]
    mock_repo.repository.get_contents.return_value = workflow_files

    # Call the function - should skip invalid file and process valid one
    available_checks = _get_available_checks_for_repo(mock_repo)

    # Should only get checks from valid file
    assert "pytest" in available_checks
    assert len(available_checks) == 1


def test_get_available_checks_ignores_non_yaml_files() -> None:
    """Test that non-YAML files are ignored"""

    workflow_yaml = """
name: Test
jobs:
  pytest:
    runs-on: ubuntu-latest
"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()

    # Mock get_contents with YAML and non-YAML files
    files = [
        create_mock_workflow_file("test.yml", workflow_yaml),
        create_mock_workflow_file("README.md", "# Not a workflow"),
        create_mock_workflow_file("script.sh", "#!/bin/bash\necho test"),
    ]
    mock_repo.repository.get_contents.return_value = files

    # Call the function
    available_checks = _get_available_checks_for_repo(mock_repo)

    # Should only process .yml file
    assert "pytest" in available_checks
    assert len(available_checks) == 1


def test_validate_required_checks_all_present() -> None:
    """Test validation when all required checks are available"""

    # Create mock repository with no warnings expected
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"

    required_checks = ["pytest", "mypy", "ruff"]
    available_checks = {"pytest", "mypy", "ruff", "extra-check"}

    # Call validation - should not raise any warnings
    _validate_required_checks(mock_repo, required_checks, available_checks)

    # Verify no warnings were issued
    mock_repo.warning.assert_not_called()


def test_validate_required_checks_some_missing() -> None:
    """Test validation when some required checks are missing"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"

    required_checks = ["pytest", "mypy", "pylint"]
    available_checks = {"pytest", "ruff"}  # mypy and pylint are missing

    # Call validation - should issue a warning
    _validate_required_checks(mock_repo, required_checks, available_checks)

    # Verify warning was issued
    mock_repo.warning.assert_called_once()

    # Check warning message contains missing checks
    warning_call = mock_repo.warning.call_args
    warning_message = warning_call[0][1]  # Second argument is the message

    assert "mypy" in warning_message
    assert "pylint" in warning_message
    assert "Available checks in workflows" in warning_message
    assert "pytest" in warning_message
    assert "ruff" in warning_message


def test_validate_required_checks_none_available() -> None:
    """Test validation when no workflows exist at all"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)
    mock_repo.repository = Mock()
    mock_repo.repository.full_name = "test/repo"

    required_checks = ["pytest", "mypy"]
    available_checks: set[str] = set()  # No workflows found

    # Call validation - should issue a warning
    _validate_required_checks(mock_repo, required_checks, available_checks)

    # Verify warning was issued
    mock_repo.warning.assert_called_once()

    # Check warning message mentions no workflows
    warning_call = mock_repo.warning.call_args
    warning_message = warning_call[0][1]

    assert "pytest" in warning_message
    assert "mypy" in warning_message
    assert "No workflow files found" in warning_message


def test_validate_required_checks_empty_required() -> None:
    """Test validation when no checks are required"""

    # Create mock repository
    mock_repo = Mock(spec=RepoLinter)

    required_checks: List[str] = []
    available_checks: set[str] = {"pytest", "mypy"}

    # Call validation - should do nothing
    _validate_required_checks(mock_repo, required_checks, available_checks)

    # Verify no warnings were issued
    mock_repo.warning.assert_not_called()
