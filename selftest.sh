#!/bin/bash

# shellcheck disable=SC1091

# shellcheck disable=SC2068
python -m github_linter -o yaleman -r github_linter $@
