#!/bin/bash

LOG_LEVEL=DEBUG poetry run uvicorn github_linter.web:app --reload-dir ./github_linter --debug
