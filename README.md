# Quantitative Relaxations for Arrow's Axioms

This repository contains replication analyses of quantitative fairness metrics for elections in
New York City, Portland, and Scotland, alongside synthetic elections generated with a
Bradley–Terry model. The dataset runners compute the metrics and produce the main figures and
tables. For input sources, experiment settings, and additional analyses, see the
[replication guide](documentation/replication.md).

## Quick start

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) to install Python and manage the
repository's dependencies. Its standalone installer runs in a terminal on macOS or Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, use the PowerShell installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Once installation finishes, restart your terminal so the updated `PATH` takes effect and check
that uv is available:

```sh
uv --version
```

From the repository root, the following commands prepare the environment, check the installation,
and run the New York pipeline:

```sh
uv sync --locked
uv run --locked pytest
uv run --locked python scripts/smoke_test.py
./scripts/run_ny_pipeline.sh
```

The first command installs the dependencies from `uv.lock` into `.venv/` and downloads Python 3.12
if needed. On Windows, you will need to launch the New York analysis with
`uv run --locked python scripts/replicate.py ny`.

The cleaned New York and Portland inputs are included in the repository, so those analyses are
ready to run after setup. Scotland and Bradley–Terry (BT) need additional downloads, with Git LFS
required for the BT inputs. Retrieval commands are in the replication guide.

The BT inputs may also be regenerated using the pipeline, but the resulting 84,000 profiles
take a long time to generate. It is therefore recommended to use the supplied inputs unless you
want to explore different BT parameters.

To keep a new computation separate from the default outputs beneath the repository root, pass
`--output-dir results/new-run`. Existing profiles, preference interval dataframes, metric scores,
and election results are preserved, so recomputing them requires a new output directory or moving
the saved files manually. Figures and other derived outputs are overwritten on repeat runs.

## Reproducibility

Reuse the supplied preference profiles to keep the input sample fixed. Generating a new sample
should produce statistically similar results, although changes to random-number and execution
paths prevent exact reproduction of the original profiles. Randomized voting and metric
calculations may also differ from the saved results even with fixed inputs.

## Layout

| Location                                      | Purpose                                                 |
| --------------------------------------------- | ------------------------------------------------------- |
| `code/voting_metrics_main_code/`              | Authoritative metrics and voting rules                  |
| [`code/pipelines/`](code/pipelines/README.md) | Dataset collectors, plotters, and analysis index        |
| [`scripts/`](scripts/README.md)               | Replication runners, input retrieval, and smoke check   |
| `code/config/`                                | Experiment selections, including the BT profile folders |
| `code/tests/`                                 | Scientific correctness and data-preservation checks     |
| `code/preprocessing/`                         | Election input cleaning and slate support analysis      |
| `code/archive/`                               | Superseded source snapshots, notebooks, and figures     |
| `documentation/`                              | Replication guide and input provenance                  |
| `data/`                                       | Preserved inputs; optional large downloads              |
| `stats/`, `plots/`                            | Saved statistics and regenerable figures                |
| `results/generated/`                          | Optional ignored output root                            |

The reusable metrics and voting rules live in `code/voting_metrics_main_code/`.

## Replication commands

```sh
./scripts/run_ny_pipeline.sh
./scripts/run_portland_pipeline.sh
./scripts/run_scottish_pipeline.sh --n-jobs 4
./scripts/run_bt_pipeline.sh --n-jobs 4
```

Each runner collects scores and produces its main outputs by default. If you already have the
scores, `--mode figures` rebuilds figures and tables from the statistics beneath the selected
`--output-dir`, while `--mode stats` collects scores alone. To use saved statistics elsewhere,
pass `--stats-dir stats`, or select a BT statistics tree with `--bt-stats-dir` in figures mode.

Since full computations can be expensive, start with the smoke check to confirm the installation.
The [scripts guide](scripts/README.md) explains the runner options, and individual analyses expose
their options through `--help`.
