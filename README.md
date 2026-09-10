# Quantitative Relaxations for Arrow's Axioms

Replication analyses for quantitative fairness metrics in NY, Portland, Scottish, and synthetic
Bradley–Terry elections. See [the replication guide](docs/replication.md) for artifact mappings,
input provenance, experiment settings, limitations, and release work still requiring author input.

## Quick start

Install Python 3.12 and uv, then:

```sh
uv sync --locked
uv run --locked pytest
uv run --locked python scripts/smoke_test.py
./scripts/run_ny_pipeline.sh
```

Environment synchronization installs the locked dependencies without modifying data. NY and Portland
cleaned inputs are tracked; optional Scottish and BT retrieval commands are in the guide. BT inputs
use Git LFS. New results go to `results/generated/`. Existing data and historical results remain
in place.

## Reproducibility

The archived preference profiles were generated with seeded runs of an older version of the code.
Regenerating them with this version follows different random-number and execution paths, so a full
rerun should produce statistically similar results, not exactly the same profiles or numerical
values. Reusing the archived profiles keeps the input sample fixed; randomized voting and metric
calculations may still differ from the historical runs. See the replication guide for details.

## Layout

| Location                            | Purpose                                                            |
| ----------------------------------- | ------------------------------------------------------------------ |
| `voting_metrics_main_code/`         | Authoritative metrics and voting rules                             |
| [`pipelines/`](pipelines/README.md) | Dataset collectors, plotters, and analysis index                   |
| `scripts/`                          | Maintained replication runners, input retrieval, and smoke example |
| `config/`                           | Experiment selections, including the BT profile folders            |
| `tests/`                            | Maintained behavior and replication checks                         |
| `data/`                             | Preserved inputs; optional large downloads                         |
| `stats/`, `plots/`                  | Preserved historical results, pending publication designation      |
| `results/generated/`                | Ignored outputs of new runs                                        |
| `docs/`                             | Replication inventory, provenance, and baseline                    |
| `archive/`                          | Preserved superseded source snapshots                              |
| `notebooks/`, `other_files/`        | Historical notebooks and preparation utilities                     |

Import metrics and voting rules directly from `voting_metrics_main_code`. Run commands through
`scripts/`; there are no root forwarding scripts. The ignored `paper/` and `dev_files/` directories
contain local research material and are not included in a clone.

## Replication commands

```sh
./scripts/run_ny_pipeline.sh
./scripts/run_portland_pipeline.sh
./scripts/run_scottish_pipeline.sh --n-jobs 4
./scripts/run_bt_pipeline.sh --n-jobs 4
```

Use `--mode figures --stats-dir stats` to regenerate presentation artifacts from existing
statistics, or `--mode stats` to compute without plotting. BT reference trees can be selected with
`--bt-stats-dir` in figures mode. Full runs can be expensive; start with the smoke example.

All commands, numerical conventions, and known provenance gaps are documented in
[docs/replication.md](docs/replication.md). Exact paper figure numbers and the final citation await
author designation.
