#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

# python ${SCRIPT_DIR}/pipelines/scottish/collect_stats_scottish.py

for variant in "worst_case" "average"
do
    for tiebreak in "random" "lex"
    do
        python ${SCRIPT_DIR}/pipelines/scottish/create_scottish_outputs.py --variant ${variant} --tiebreak ${tiebreak}
    done
done