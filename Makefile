FULLNAME ?= kanidm/kanidm


.DEFAULT: precommit

.PHONY: precommit
precommit: ruff types test

.PHONY: jslint
jslint:
	find github_linter -name '*.js' -or -name '*.css' -not -name 'pico.min.css' | xargs biome check --json-formatter-enabled=false

.PHONY: ruff
ruff:
	uv run ruff check github_linter tests

.PHONY: types
types:
	uv run ty check

.PHONY: test
test:
	uv run pytest github_linter tests

.PHONY: docker_build
docker_build:
	docker build -t 'ghcr.io/yaleman/github_linter:latest' \
		.

.PHONY: docker_run
docker_run: docker_build
	docker run --rm -it \
		-p 8000:8000 \
		--env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
		'ghcr.io/yaleman/github_linter:latest' \
		python -m github_linter.web

.PHONY: container/workflow_stats
container/workflow_stats:
	docker run --rm -it \
		--env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
		'ghcr.io/yaleman/github_linter:latest' \
		python -m github_linter.workflow_stats -f $(FULLNAME)