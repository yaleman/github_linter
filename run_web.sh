#!/bin/bash

LOG_LEVEL=INFO \
    uvicorn \
    github_linter.web:app
