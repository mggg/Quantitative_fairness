#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

# python ${SCRIPT_DIR}/pipelines/scottish/collect_stats_scottish.py

for variant in "worst_case" "average"; do
    for tiebreak in "random" "lex"; do
        echo "Creating boxplots for variant ${variant} and tiebreak ${tiebreak}"
        uv run ${SCRIPT_DIR}/pipelines/scottish/create_scottish_boxplots_variant_tiebreak.py \
            --variant ${variant} \
            --tiebreak ${tiebreak}
    done
done

echo "Creating overall boxplots"
uv run ${SCRIPT_DIR}/pipelines/scottish/create_scottish_boxplot.py
echo "Creating scatterplots"
uv run ${SCRIPT_DIR}/pipelines/scottish/create_scottish_scatterplots.py
echo "Creating CSVs"
uv run ${SCRIPT_DIR}/pipelines/scottish/make_scottish_csv_limited.py