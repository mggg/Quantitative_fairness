#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}
source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

PROFILE_ROOT="${SCRIPT_DIR}/data/preference_profiles"

if [[ ! -d "${PROFILE_ROOT}" ]] || ! find "${PROFILE_ROOT}" -type f -name "*.csv" -print -quit | grep -q .; then
    echo "No BT preference profiles found. Generating profiles first."
    uv run pipelines/bradley-terry/generate_BT_profiles.py
else
    echo "BT preference profiles already present. Skipping generation."
fi

for input_folder in $(find ${SCRIPT_DIR}/data/preference_profiles/ -type d -name "*b_proportion*"); do
    echo "Processing input folder: $input_folder"

    n_seats=3
    for metric in "sigma_UM" "sigma_UM_winner_set"; do
        for variant in "worst_case" "average"; do
            for interpolation_type in "asin" "odds" "linear"; do
                for election_type in "borda" "plurality" "stv"; do
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

    for metric in "sigma_IIA" "sigma_IIA_winner_set"; do
        for variant in "worst_case" "average"; do
            for interpolation_type in "None"; do
                for election_type in "borda" "plurality" "stv"; do
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
done

candidate_count_combinations=(
    "2 6"
    "4 4"
    "6 2"
    "2 8"
    "5 5"
    "8 2"
)

b_bloc_proportions=(0.5 0.6 0.7 0.8 0.9)

cohesion_combinations=(
    "0.7 0.7"
    "0.7 0.9"
    "0.9 0.7"
    "0.9 0.9"
)

for cand_pair in "${candidate_count_combinations[@]}"; do
    read -r n_a_cands n_b_cands <<< "${cand_pair}"
    for b_prop in "${b_bloc_proportions[@]}"; do
        for cohesion_pair in "${cohesion_combinations[@]}"; do
            read -r a_coh b_coh <<< "${cohesion_pair}"
            uv run pipelines/bradley-terry/compute_proportionality.py \
                --n-a-cand ${n_a_cands} \
                --n-b-cand ${n_b_cands} \
                --b-prop ${b_prop} \
                --a-coh ${a_coh} \
                --b-coh ${b_coh}
        done
    done
done

for f in $(find ${SCRIPT_DIR}/pipelines/bradley-terry/make_plots -name "*.py"); do
    uv run $f
done
