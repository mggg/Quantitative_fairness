#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))

python ${SCRIPT_DIR}/pipelines/scottish/collect_stats_scottish.py
python ${SCRIPT_DIR}/pipelines/scottish/create_scottish_outputs.py