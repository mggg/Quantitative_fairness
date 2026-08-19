#!/usr/bin/env bash


SCRIPT_DIR=$(dirname $(realpath $0))

source .venv/bin/activate
output_file="bt_settings_final_set.txt"
printf "" > $output_file


for d in $(find /share/duchin/personal_dirs/peter/Quantitative_fairness/data/preference_profiles_2_bloc_final_experiment/**/ -type d | grep -i 'b_prop')
do 
                    echo $d  >> $output_file
    # for metric in "sigma_UM" "sigma_UM_winner_set"
    # do
    #     for variant in "worst_case" "average"
    #     do
    #         for interpolation_type in "asin" "odds" "linear"
    #         do
    #             for election_type in "borda" "plurality" "stv"
    #             do
                    # echo $d $metric $variant $interpolation_type $election_type >> $output_file
    #             done
    #         done
    #     done
    # done
done


# for d in $(find /share/duchin/personal_dirs/peter/Quantitative_fairness/data/preference_profiles_2_bloc_final_experiment/**/ -type d)
# do 
#     for metric in "sigma_IIA" "sigma_IIA_all_subset" "sigma_IIA_winner_set"
#     do
#         for variant in "worst_case" "average"
#         do
#             for interpolation_type in "asin" "odds" "linear"
#             do
#                 for election_type in "borda" "plurality" "stv"
#                 do
#                     echo $d $metric $variant $interpolation_type $election_type >> $output_file
#                 done
#             done
#         done
#     done
# done
#
