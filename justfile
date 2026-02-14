


[private]
default:
    just --list

check: format lint jslint
  just test -m 'not\ network'

set positional-arguments

test *args='':
    uv run pytest {{ args }}

lint:
    uv run ty check

format:
    uv run ruff format tests github_linter
    uv run ruff check tests github_linter

jslint:
    biome check --verbose

docker_build:
    docker build -t 'ghcr.io/yaleman/github_linter:latest' \
        .

docker_run:
    docker run --rm -it \
        -p 8000:8000 \
        --env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
        'ghcr.io/yaleman/github_linter:latest' \
        python -m github_linter.web

workflow_stats:
    docker run --rm -it \
        --env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
        'ghcr.io/yaleman/github_linter:latest' \
        python -m github_linter.workflow_stats -f yaleman/pygoodwe