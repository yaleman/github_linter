"""Tests for the web server CLI."""

from typing import Any

import pytest
from click.testing import CliRunner

from github_linter.web import UVICORN_WORKERS
from github_linter.web.__main__ import cli


def test_cli_starts_multiple_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    """The web server should retain its configured worker concurrency."""
    run_arguments: dict[str, Any] = {}

    def capture_run_arguments(**kwargs: Any) -> None:
        run_arguments.update(kwargs)

    monkeypatch.setattr("github_linter.web.__main__.uvicorn.run", capture_run_arguments)

    result = CliRunner().invoke(cli)

    assert result.exit_code == 0
    assert run_arguments["workers"] == UVICORN_WORKERS
