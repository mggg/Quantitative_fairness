#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))

# # NOTE: Uncomment the following line to regenerate the profiles
# python ${SCRIPT_DIR}/pipelines/bradley-terry/generate_BT_profiles.py
for n_seats in 1 2 3 4 5
do
    for n_cands in 6 7 8 9
    do 
    for metric in "sigma_IIA" "sigma_UM" "sigma_IIA_winner_set" "sigma_UM_winner_set"
    do
    for election_type in "borda" "3-approval" "2-approval" "plurality" "stv" 
    do
        python ${SCRIPT_DIR}/pipelines/bradley-terry/collect_stats_BT.py --n-seats $n_seats --n-cands $n_cands --metric $metric --election-type $election_type
    done
    done
    done
    python ${SCRIPT_DIR}/pipelines/bradley-terry/create_sigma_output.py --n-seats $n_seats
done
