#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

n_seats=3
for metric in "sigma_UM" "sigma_UM_winner_set"
do
    for variant in "worst_case" "average"
    do
        for interpolation_type in "asin" "odds" "linear"
        do
            for election_type in "borda" "plurality" "stv"
            do
                uv run pipelines/bradley-terry/collect_stats_BT.py \
                    --input-folder $input_folder \
                    --n-seats $n_seats \
                    --metric $metric \
                    --variant $variant \
                    --interpolation-type $interpolation_type \
                    --election-type $election_type
            done
        done
    done
done

for metric in "sigma_IIA" "sigma_IIA_winner_set"
do
    for variant in "worst_case" "average"
    do
        for interpolation_type in "None"
        do
            for election_type in "borda" "plurality" "stv"
            do
                uv run pipelines/bradley-terry/collect_stats_BT.py \
                    --input-folder $input_folder \
                    --n-seats $n_seats \
                    --metric $metric \
                    --variant $variant \
                    --interpolation-type $interpolation_type \
                    --election-type $election_type
            done
        done
    done
done

# NOTE: Uncomment me to run the all subset metrics. These will take a LONG time to run,
# so they might be better relegated to a cluster computer

# for metric in "sigma_IIA_all_subset" "sigma_IIA_winner_set_all_subset"
# do
#     for variant in "worst_case" "average"
#     do
#         for interpolation_type in "None"
#         do
#             for election_type in "borda" "plurality" "stv"
#             do
#                 uv run pipelines/bradley-terry/collect_stats_BT.py \
#                     --input-folder $input_folder \
#                     --n-seats $n_seats \
#                     --metric $metric \
#                     --variant $variant \
#                     --interpolation-type $interpolation_type \
#                     --election-type $election_type
#             done
#         done
#     done
# done


for f in $(find ${SCRIPT_DIR}/pipelines/bradley-terry/make_plots -name "*.py"); do
    uv run $f
done