# #!/usr/bin/env bash

mkdir -p data

# Get the scottish election data
git clone https://github.com/mggg/scot-elex.git data/scot-elex


# Get the NY primary data
wget https://www.vote.nyc/sites/default/files/pdf/election_results/2025/20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip && \
mkdir -p data/NY_primary_data && \
unzip 2025_Primary_CVR_2025-07-17.zip -d data/NY_primary_data && \
rm 2025_Primary_CVR_2025-07-17.zip


python other_files/clean_portland_data.py
python other_files/clean_ny_data.py