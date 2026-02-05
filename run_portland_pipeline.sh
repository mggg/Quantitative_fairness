#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

uv run ${SCRIPT_DIR}/pipelines/portland/collect_stats_portland.py

echo "Running Portland clustering diagnostics"
uv run ${SCRIPT_DIR}/pipelines/portland/short_burst_clustering.py
uv run ${SCRIPT_DIR}/pipelines/portland/brute_force_clustering.py
