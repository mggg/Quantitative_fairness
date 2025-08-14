#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

python ${SCRIPT_DIR}/pipelines/NY/collect_stats_ny.py
