#!/usr/bin/env bash

python generate_BT_profiles.py
python collect_stats_BT.py
python create_sigma_output.py