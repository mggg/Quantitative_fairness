#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

# # NOTE: Uncomment the following line to regenerate the profiles
# python ${SCRIPT_DIR}/pipelines/bradley-terry/generate_BT_profiles.py

# for n_seats in 1 2 3 4 5; do
#     for n_cands in 6 7 8 9; do
#         for metric in "sigma_IIA" "sigma_UM" "sigma_IIA_winner_set" "sigma_UM_winner_set"; do
#             for election_type in "borda" "3-approval" "2-approval" "plurality" "stv"; do
#                 python ${SCRIPT_DIR}/pipelines/bradley-terry/collect_stats_BT.py --n-seats $n_seats --n-cands $n_cands --metric $metric --election-type $election_type
#             done
#         done
#     done
# done

# for n_seats in 1 2 3 4 5; do
#     for n_cands in 6 7 8 9; do
#         for alpha in 0.33 0.50 1.00 2.00 3.00; do
#             for metric in "sigma_UM" "sigma_UM_winner_set"; do
#                 for variant in "worst_case" "average"; do
#                     for interpolation_type in "asin" "odds"; do
#                         for election_type in "borda" "3-approval" "2-approval" "plurality" "stv" "ranked-pairs"; do
#                             for tiebreak in "lex" "random"; do
#                                 python ${SCRIPT_DIR}/pipelines/bradley-terry/collect_stats_BT.py \
#                                     --n-seats $n_seats \
#                                     --n-cands $n_cands \
#                                     --alpha-value $alpha \
#                                     --metric $metric \
#                                     --variant $variant \
#                                     --interpolation-type $interpolation_type \
#                                     --election-type $election_type \
#                                     --tiebreak $tiebreak \
#                                     --show-progress
#                             done
#                         done
#                     done
#                 done
#             done
#         done
#     done
# done

for n_seats in 1 2 3 4 5; do
    for n_cands in 6 7 8 9; do
        for alpha in 0.33 0.50 1.00 2.00 3.00; do
            for metric in "sigma_UM" "sigma_UM_winner_set"; do
                for variant in "worst_case" "average"; do
                    for interpolation_type in "asin" "odds"; do
                        for election_type in "random"; do
                            for tiebreak in "lex" "random"; do
                                python ${SCRIPT_DIR}/pipelines/bradley-terry/collect_stats_BT.py \
                                    --n-seats $n_seats \
                                    --n-cands $n_cands \
                                    --alpha-value $alpha \
                                    --metric $metric \
                                    --variant $variant \
                                    --interpolation-type $interpolation_type \
                                    --election-type $election_type \
                                    --tiebreak $tiebreak \
                                    --show-progress
                            done
                        done
                    done
                done
            done
        done
    done
done

# parallel --bar -j"$(nproc)" \
#     python "${SCRIPT_DIR}/pipelines/bradley-terry/collect_stats_BT.py" \
#     --n-seats {1} --n-cands {2} --alpha-value {3} --metric {4} --variant {5} \
#     --interpolation-type {6} --election-type {7} --tiebreak {8} ::: \
#     1 2 3 4 5 ::: 6 7 8 9 ::: 0.33 0.50 1.00 2.00 3.00 ::: sigma_UM sigma_UM_winner_set ::: \
#     worst_case average ::: asin odds ::: \
#     borda '3-approval' '2-approval' plurality stv ranked-pairs ::: \
#     lex random

# for n_seats in 1 2 3 4 5; do
#     for variant in "worst_case" "average"; do
#         for tiebreak in "lex" "random"; do
#             python ${SCRIPT_DIR}/pipelines/bradley-terry/create_sigma_output.py --n-seats $n_seats --variant $variant --tiebreak $tiebreak
#         done
#     done
# done
