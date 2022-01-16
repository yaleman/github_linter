#!/bin/bash

echo "running pylint on module"
poetry run python -m pylint --rcfile=.pylintrc github_linter/
echo "running pylint on tests"
poetry run python -m pylint --rcfile=.pylintrc test_*.py
