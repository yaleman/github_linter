.DEFAULT: precommit

.PHONY: precommit
precommit: ruff mypy pytest

.PHONY: ruff
ruff:
	poetry run ruff github_linter tests

.PHONY: mypy
mypy:
	poetry run mypy --strict github_linter tests

.PHONY: pytest
pytest:
	poetry run pytest github_linter tests

