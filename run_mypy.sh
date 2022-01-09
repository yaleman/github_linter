#!/bin/bash

# shellcheck disable=SC1091
source venv/bin/activate

python3 -m mypy github_linter/
