


[private]
default:
    just --list

workflow_stats:
    docker run --rm -it \
        --env-file .envrc -e "GITHUB_TOKEN=${GITHUB_TOKEN}" \
        'ghcr.io/yaleman/github_linter:latest' \
        python -m github_linter.workflow_stats -f yaleman/pygoodwe