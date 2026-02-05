#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
REPO_ROOT=$(realpath "${SCRIPT_DIR}/..")
cd "${REPO_ROOT}"
source "${REPO_ROOT}/.venv/bin/activate"

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

uv run "${REPO_ROOT}/pipelines/NY/collect_stats_ny.py"
