#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
REPO_ROOT=$(realpath "${SCRIPT_DIR}/..")
cd "${REPO_ROOT}"
source "${REPO_ROOT}/.venv/bin/activate"

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

uv run "${REPO_ROOT}/pipelines/scottish/collect_stats_scottish.py"

for variant in "worst_case" "average"; do
    for tiebreak in "random" "lex"; do
        echo "Creating boxplots for variant ${variant} and tiebreak ${tiebreak}"
        uv run "${REPO_ROOT}/pipelines/scottish/create_scottish_boxplots_variant_tiebreak.py" \
            --variant ${variant} \
            --tiebreak ${tiebreak}
    done
done

echo "Creating overall boxplots"
uv run "${REPO_ROOT}/pipelines/scottish/create_scottish_boxplot.py"
echo "Creating scatterplots"
uv run "${REPO_ROOT}/pipelines/scottish/create_scottish_scatterplots.py"
echo "Creating CSVs"
uv run "${REPO_ROOT}/pipelines/scottish/make_scottish_csv_limited.py"
