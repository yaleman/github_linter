FULLNAME ?= kanidm/kanidm


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

.PHONY: container/workflow_stats
container/workflow_stats:
	docker run --rm -it --env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" 'ghcr.io/yaleman/github_linter:latest' python -m github_linter.workflow_stats -f $(FULLNAME)