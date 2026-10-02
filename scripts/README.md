# Replication scripts

Use these scripts to run a dataset analysis, prepare its inputs, or rebuild a summary table from
saved scores. The calculations and plotting code live in
[`code/pipelines/`](../code/pipelines/README.md), with input requirements and the full sequence
described in the [replication guide](../documentation/replication.md). Run the examples below from
the repository root after preparing the environment with `uv sync --locked`.

## Dataset runners

The shell runners select a dataset and pass your options to `replicate.py`, which executes the
workflow's commands in order. Alongside the primary analyses listed below,
additional analyses are available individually through the pipeline index.

| Script                                                 | Purpose                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| [`run_ny_pipeline.sh`](run_ny_pipeline.sh)             | Compute New York mayoral metrics and export the summary table.                  |
| [`run_portland_pipeline.sh`](run_portland_pipeline.sh) | Compute district metrics, export the summary table, and render boost matrices.  |
| [`run_scottish_pipeline.sh`](run_scottish_pipeline.sh) | Compute Scottish metrics, render UM–IIA scatterplots, and export metric tables. |
| [`run_bt_pipeline.sh`](run_bt_pipeline.sh)             | Compute two-bloc BT metrics and render UM–IIA scatterplots.                     |

You can also call [`replicate.py`](replicate.py) directly with `ny`, `portland`, `scottish`, or
`bt`. For example, these commands run the Portland analysis, rebuild BT figures from saved scores,
and run the Scottish analysis with four workers:

```sh
./scripts/run_portland_pipeline.sh
./scripts/run_bt_pipeline.sh --mode figures
uv run --locked python scripts/replicate.py scottish --n-jobs 4
```

By default, `--mode all` collects scores and then produces figures and tables. Use `--mode stats`
for collection alone, or `--mode figures` to rebuild figures and tables from saved scores.
Portland's optional `--diagnostics` also runs the clustering searches.

To keep a run's outputs together, use `--output-dir` to choose the root for its `stats/`, `plots/`,
and `tables/` directories. That root defaults to the repository and supplies the statistics for
figures mode unless you select another source with `--stats-dir` or BT's `--bt-stats-dir`.
Collectors preserve existing results, whereas figures and exported tables may be overwritten.
Use a new output directory or move the saved results manually when you want to recompute them.

For BT, `--settings-file` selects the list of profile folders to analyze. Without it, the runner
uses `code/config/bt_profiles.txt`.

## Input preparation and table export

The optional Scottish and BT inputs are prepared by [`fetch_data.py`](fetch_data.py). For
Scotland, it clones the election dataset at the revision recorded in the script into
`data/scot-elex/`. For BT, it extracts `data/preference_profiles.tar.xz` to
`data/preference_profiles/`, or prints the required retrieval command if the archive is still a
Git LFS pointer. Both operations require a new destination, which you can choose with
`--destination` if you want the inputs outside the default location.

Once the BT profiles are available, [`generate_settings.py`](generate_settings.py) creates a
sorted folder list for the collector. It reads `data/preference_profiles/` by default, or the
directory selected with `--profile-root`, and writes the list to the required `--output` path,
replacing an existing settings file. The profiles themselves must already exist.

For New York and Portland, [`export_tables.py`](export_tables.py) turns saved metric JSONs into
`tables/ny.csv` or `tables/portland.csv`, with one row per election and voting rule. The dataset
runners include this step, but you can call it separately to rebuild a table without recomputing
the metrics. Use `--stats-dir` and `--output-dir` to select its inputs and output location.

```sh
uv run --locked python scripts/fetch_data.py scottish
uv run --locked python scripts/generate_settings.py --output /tmp/bt_profiles.txt
uv run --locked python scripts/export_tables.py portland
```

## Smoke check

To check the installation without downloading research inputs, run
[`smoke_test.py`](smoke_test.py). It creates a tiny unanimous election in a temporary directory,
saves and reloads its CSV, and runs the BT collector with Borda and two seats. All four metric
JSONs must contain the expected score of 1.0.

```sh
uv run --locked python scripts/smoke_test.py
```
