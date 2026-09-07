#!/bin/bash

n_seats=3
tiebreak="lex"

uv run pipelines/bradley-terry/collect_stats_final_set_v2.py \
    --settings-file settings.txt \
    --n-seats "$n_seats" \
    --election-type random \
    --tiebreak "$tiebreak"
