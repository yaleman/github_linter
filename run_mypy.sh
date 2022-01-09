#!/bin/bash

# shellcheck disable=SC1091
source venv/bin/activate


python -m mypy github_linter/
