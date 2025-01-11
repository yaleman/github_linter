#!/bin/bash

LOG_LEVEL=DEBUG uvicorn github_linter.web:app --reload-dir ./github_linter --debug
