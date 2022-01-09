#!/bin/bash

# shellcheck disable=SC1091
source venv/bin/activate

echo "running pylint on module"
python -m pylint --rcfile=.pylintrc github_linter/
echo "running pylint on tests"
python -m pylint --rcfile=.pylintrc test_*.py

