# Replication scripts

This directory contains the dataset runners, input preparation utilities, and a small smoke check.
The calculations and plotting code live in [`code/pipelines/`](../code/pipelines/README.md). For
input requirements and the full replication sequence, see the
[replication guide](../documentation/replication.md).

Run the examples below from the repository root after `uv sync --locked`.

## Dataset runners

Each shell script calls `replicate.py` with its dataset selected and forwards any supplied
options. These runners execute the primary workflow for a dataset; additional analyses are listed
in the pipeline index.

| Script                                                 | Purpose                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------- |
| [`run_ny_pipeline.sh`](run_ny_pipeline.sh)             | Compute New York mayoral metrics and export the summary table.                  |
| [`run_portland_pipeline.sh`](run_portland_pipeline.sh) | Compute district metrics, export the summary table, and render boost matrices.  |
| [`run_scottish_pipeline.sh`](run_scottish_pipeline.sh) | Compute Scottish metrics, render UM–IIA scatterplots, and export metric tables. |
| [`run_bt_pipeline.sh`](run_bt_pipeline.sh)             | Compute two-bloc BT metrics and render UM–IIA scatterplots.                     |

[`replicate.py`](replicate.py) defines these workflows, prints their commands, and runs them in
order. Call it directly with `ny`, `portland`, `scottish`, or `bt`, or use the corresponding shell
script.

```sh
./scripts/run_portland_pipeline.sh --dry-run
./scripts/run_bt_pipeline.sh --mode figures
uv run --locked python scripts/replicate.py scottish --n-jobs 4
```

`--mode all` is the default. `--mode stats` runs metric collection, while `--mode figures` uses
saved scores for the plotting/table stage. `--dry-run` prints commands without running them.
Portland's optional `--diagnostics` adds the clustering searches.

`--output-dir` selects a run root containing `stats/`, `plots/`, and `tables/`; it defaults to the
repository. In figures mode, inputs default to that run root's statistics. Use `--stats-dir` or
BT's `--bt-stats-dir` to select saved scores elsewhere. BT uses `code/config/bt_profiles.txt`
unless `--settings-file` selects another profile-folder list. Collectors skip existing results;
move them manually before recomputing. Figures and exported tables may overwrite existing outputs.

## Input preparation and table export

[`fetch_data.py`](fetch_data.py) prepares optional inputs for `bt` or `scottish`. For BT, it
extracts `data/preference_profiles.tar.xz` to `data/preference_profiles/`. If the archive is still
a Git LFS pointer, it prints the required LFS retrieval command. For Scotland, it clones the
election dataset at the revision recorded in the script into `data/scot-elex/`. It refuses
existing destinations; `--destination` selects a different directory.

[`generate_settings.py`](generate_settings.py) lists existing BT profile folders in sorted order.
Use it when preparing a profile-folder list for the BT collector. It reads
`data/preference_profiles/` by default, or `--profile-root`, and writes the required `--output`
file, replacing that file if it exists. It does not generate profiles.

[`export_tables.py`](export_tables.py) converts saved `ny` or `portland` metric JSONs to
`tables/ny.csv` or `tables/portland.csv`, with one row per election and voting rule. The dataset
runners already call it; use it separately to rebuild a table without recomputing metrics. It
accepts `--stats-dir` and `--output-dir`.

```sh
uv run --locked python scripts/fetch_data.py scottish
uv run --locked python scripts/generate_settings.py --output /tmp/bt_profiles.txt
uv run --locked python scripts/export_tables.py portland
```

## Smoke check

[`smoke_test.py`](smoke_test.py) creates a tiny unanimous election, saves and reloads its CSV, and
runs the BT collector with Borda and two seats. It checks that all four metric JSONs contain the
expected score of 1.0. Everything runs in a temporary directory; no research inputs are needed.

```sh
uv run --locked python scripts/smoke_test.py
```
