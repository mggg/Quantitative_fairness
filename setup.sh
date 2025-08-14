#!/usr/bin/env bash

SCRIPT_DIR=$(dirname $(realpath $0))
cd ${SCRIPT_DIR}

uv sync
if [[ $? -ne 0 ]]; then
    echo "Failed to run 'uv sync'. Please make sure that uv is installed on your system and in your path."
    exit 1
fi

source ${SCRIPT_DIR}/.venv/bin/activate

if [[ $? -ne 0 ]]; then
    echo "Failed to activate virtual environment. Please check to make sure you have run 'uv sync'"
    exit 1
fi

# Get the scottish election data
git clone https://github.com/mggg/scot-elex.git data/scot-elex

# Get the NY primary data
wget https://www.vote.nyc/sites/default/files/pdf/election_results/2025/20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip && \
mkdir -p ${SCRIPT_DIR}/data/NY_primary_data && \
unzip 2025_Primary_CVR_2025-07-17.zip -d ${SCRIPT_DIR}/data/NY_primary_data && \
rm 2025_Primary_CVR_2025-07-17.zip

# Unzip previous preference profiles.
unzip ${SCRIPT_DIR}/data/preference_profiles.zip -d data/preference_profiles

# Clean the 
python ${SCRIPT_DIR}/other_files/clean_portland_data.py
python ${SCRIPT_DIR}/other_files/clean_ny_data.py
