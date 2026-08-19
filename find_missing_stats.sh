#!/usr/bin/env bash



SCRIPT_DIR=$(dirname $(realpath $0))

source .venv/bin/activate
output_file="slow_sigma_2.txt"
printf "" > $output_file


for n_seats in 1 2 3 4 5
do
for n_cands in 6 7 8 9
do 
for metric in "sigma_IIA" "sigma_IIA_all_subset" "sigma_IIA_winner_set"
do
for election_type in "borda" "3-approval" "2-approval" "plurality" "stv" "ranked-pairs"
do
for alpha in "0.33" "0.50" "1.00" "2.00" "3.00"
do
for variant in "worst_case" "average"
do
for tiebreak in "random" "lex"
do
    output_folder="./stats/bt_profile_stats/${n_seats}_seats/${metric}/0${n_cands}/alpha_${alpha}"
    file_base="METRIC_${metric}__SEATS_${n_seats}__NCANDS_${n_cands}__ALPHA_${alpha}__TYPE_${election_type}__VARIANT_${variant}__TIEBREAK_${tiebreak}__INTERP_None.json"
    file="${output_folder}/${file_base}"
    if [ ! -f "$file" ]; then
        # echo "${file_base} does not exist"
        echo "${n_seats} ${n_cands} ${alpha} ${metric} ${variant} None ${election_type} ${tiebreak}" >> $output_file
    fi
done
done
done
done
done
done
done



for n_seats in 1 2 3 4 5
do
for n_cands in "06" "07" "08" "09"
do 
for metric in "sigma_UM" "sigma_UM_winner_set"
do
for election_type in "borda" "3-approval" "2-approval" "plurality" "stv" "ranked-pairs"
do
for alpha in "0.33" "0.50" "1.00" "2.00" "3.00"
do
for variant in "worst_case" "average"
do
for tiebreak in "random" "lex"
do
for interp in "asin" "odds"
do
    output_folder="./stats/bt_profile_stats/${n_seats}_seats/${metric}/${n_cands}/alpha_${alpha}"
    file="${output_folder}/METRIC_${metric}__SEATS_${n_seats}__NCANDS_${n_cands}__ALPHA_${alpha}__TYPE_${election_type}__VARIANT_${variant}__TIEBREAK_${tiebreak}__INTERP_None.json"
    if [ -f "$file" ]; then      
        echo "${n_seats} ${n_cands} ${alpha} ${metric} ${variant} None ${election_type} ${tiebreak}" >> $output_file
    fi
done
done
done
done
done
done
done
done




