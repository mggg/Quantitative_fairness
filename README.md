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

The test suite checks metric values, numerical summaries, seeded reproducibility, and protection
against overwriting saved data. The separate smoke example runs a tiny election through CSV loading,
metric computation, and JSON export in a temporary directory. Neither command needs the research
datasets.

Environment synchronization installs the locked dependencies without modifying data. NY and Portland
cleaned inputs are tracked; optional Scottish and BT retrieval commands are in the guide. BT inputs
use Git LFS. Runners and standalone analyses default to the repository run root, writing to `stats/` and
`plots/`. Use `--output-dir results/new-run` for a separate computation. Preference profiles, preference interval dataframes, and saved
metric scores or election results are never replaced. Move those files manually to recompute them.
Figures and other derived outputs are overwritten by default.

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
| `tests/`                            | Scientific correctness and data-preservation checks                |
| `data/`                             | Preserved inputs; optional large downloads                         |
| `stats/`, `plots/`                  | Saved statistics and regenerable figures                           |
| `results/generated/`                | Optional ignored output root                                       |
| `docs/`                             | Replication inventory, provenance, and baseline                    |
| `archive/`                          | Preserved superseded source snapshots                              |
| `notebooks/`, `other_files/`        | Historical notebooks and preparation utilities                     |

Import metrics and voting rules directly from `voting_metrics_main_code`. Run individual workflows directly, or inspect a dataset recipe with
`uv run --locked python scripts/replicate.py portland --dry-run`. The ignored `paper/` and `dev_files/` directories
contain local research material and are not included in a clone.

## Replication commands

```sh
./scripts/run_ny_pipeline.sh
./scripts/run_portland_pipeline.sh
./scripts/run_scottish_pipeline.sh --n-jobs 4
./scripts/run_bt_pipeline.sh --n-jobs 4
```

Use `--mode figures` to plot statistics beneath the selected `--output-dir`, or `--mode stats`
to compute without plotting. Pass `--stats-dir stats` to select preserved statistics explicitly. BT reference trees can be selected with
`--bt-stats-dir` in figures mode. Individual workflows expose their paths and options with `--help`. Full runs can be expensive;
start with the smoke example.

All commands, numerical conventions, and known provenance gaps are documented in
[docs/replication.md](docs/replication.md). Exact paper figure numbers and the final citation await
author designation.
