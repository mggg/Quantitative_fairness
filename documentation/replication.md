# Replication workflow

The dataset runners take prepared election inputs through metric computation to the main figures
and tables. This guide explains how to obtain those inputs, choose output locations, and run
additional analyses from saved scores. Use the [pipeline index](../code/pipelines/README.md) to
find individual scripts, and run the commands below from the repository root.

- [Setup and inputs](#setup-and-inputs)
- [Run a dataset analysis](#run-a-dataset-analysis)
- [Output locations and saved results](#output-locations-and-saved-results)
- [Metrics and reproducibility](#metrics-and-reproducibility)
- [Additional analyses](#additional-analyses)
- [Generate a synthetic sample](#generate-a-synthetic-sample)

## Setup and inputs

After following the [README setup instructions](../README.md#quick-start), you can run New York
and Portland analyses using the cleaned CSVs included in `data/`. Scotland and Bradley–Terry (BT)
require additional downloads. The inputs and their sources are listed below.

| Dataset  | Input and source                                                                                                                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NY       | `data/NY_mayor_cleaned_votekit.csv`, prepared from the [2025 primary CVRs](https://www.vote.nyc/sites/default/files/pdf/election_results/2025/20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip) |
| Portland | `data/Portland_D[1-4]_cleaned_votekit.csv`, prepared from the [Portland Postmortem CVRs](https://github.com/mggg/Portland-Postmortem/tree/main/Restructured%20Repo/CVRs/raw_votekit_csv)                      |
| Scotland | `data/scot-elex/`, retrieved from [scot-elex](https://github.com/mggg/scot-elex) at the revision pinned by the fetcher                                                                                        |
| BT       | `data/preference_profiles/`, extracted from the repository's `data/preference_profiles.tar.xz` archive                                                                                                        |

To retrieve the Scottish dataset and extract the BT profiles, run:

```sh
uv run --locked python scripts/fetch_data.py scottish
git lfs pull --include=data/preference_profiles.tar.xz
uv run --locked python scripts/fetch_data.py bt
```

The BT archive is about 1.96 GB compressed, so allow for the download and extraction. Each fetch
creates a new dataset directory and refuses an existing destination. Pass `--destination` if you
want to retrieve the inputs elsewhere.

Rebuilding the cleaned New York and Portland CSVs requires inputs beyond those used by the
runners. The New York cleaner expects an untracked `NY_mayor_all.csv`, while the Portland cleaner
downloads from a mutable upstream branch. Because the original Portland revision was not recorded,
that download may differ from the source of the supplied cleaned files.

## Run a dataset analysis

For a new computation, choose a separate output directory so the saved results stay together:

```sh
./scripts/run_ny_pipeline.sh --output-dir results/ny-run
./scripts/run_portland_pipeline.sh --output-dir results/portland-run
./scripts/run_scottish_pipeline.sh --output-dir results/scottish-run --n-jobs 4
./scripts/run_bt_pipeline.sh --output-dir results/bt-run --n-jobs 4
```

Each runner computes scores and produces the outputs listed below by default. Use `--mode stats`
for score collection alone, or `--mode figures` to rebuild figures and tables after collection. A
full computation can take many CPU-hours, so when scores are already available you can render the
outputs directly:

```sh
./scripts/run_bt_pipeline.sh --output-dir results/bt-run --mode figures
```

| Dataset  | Statistics                       | Presentation outputs                                   |
| -------- | -------------------------------- | ------------------------------------------------------ |
| NY       | `stats/ny_stats/`                | `tables/ny.csv`                                        |
| Portland | `stats/portland_stats/`          | `tables/portland.csv`, `plots/portland/boost_matrix/`  |
| Scotland | `stats/scottish_stats/`          | `plots/scottish/`, `stats/scottish_stats/*limited.csv` |
| BT       | `stats/bt_2_bloc_profile_stats/` | `plots/bt_plots/`                                      |

All paths in the table are relative to the selected output directory. For outputs beyond those
included in the runners, the additional analyses section gives commands for selected workflows,
and the pipeline index lists the available scripts and their input requirements.

## Output locations and saved results

Use `--output-dir` to select the root of a run's `stats/`, `plots/`, `tables/`, and generated
`data/` directories. The repository root is the default, and figures mode reads statistics beneath
the selected root unless you supply an input directory explicitly. This lets you keep a
computation's outputs together or render saved scores into a separate location.

| Option           | Purpose                                              | Default                                       |
| ---------------- | ---------------------------------------------------- | --------------------------------------------- |
| `--data-dir`     | Cleaned inputs and downloaded datasets               | Repository `data/`                            |
| `--output-dir`   | Run root for outputs                                 | Repository root                               |
| `--stats-dir`    | Parent of dataset statistics directories             | `<output-dir>/stats/`                         |
| `--bt-stats-dir` | BT statistics tree containing seat-count directories | `<output-dir>/stats/bt_2_bloc_profile_stats/` |
| `--seed`         | Base seed for collection or generation               | `0`                                           |
| `--n-jobs`       | Parallel workers in supported workflows              | `1`                                           |

Scripts accept the options relevant to their analysis, which you can inspect with `--help`.
Because relative paths resolve from the calling directory, this command reads repository
statistics and writes the figures into a separate run directory:

```sh
uv run --locked python code/pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats \
  --output-dir results/figure-review
```

Collectors preserve existing metric scores and election results by skipping those files. Profile
generation also preserves profiles and their paired preference interval files, so recomputing
either requires a new output directory or moving the relevant files manually. A skipped result is
reused without checking whether its settings match the current run. Figures, exported tables,
bootstrap summaries, and settings files are overwritten on repeat runs.

## Metrics and reproducibility

The main recipes measure unanimity and majoritarianism (UM) and independence of irrelevant
alternatives (IIA) for both rankings and winner sets. UM combines worst-case aggregation with
arcsin interpolation, while IIA averages over single-candidate removals. When reading the results,
note the naming difference between the paper and code: the paper uses rho for ranking metrics and
sigma for winner-set metrics, whereas the code calls the ranking metrics `sigma_UM` and
`sigma_IIA` and adds `_winner_set` for winner-set metrics.

Seat counts follow the observed elections: one for New York, three for Portland, and the count
specified in each Scottish input. BT defaults to three seats, adjustable with `--n-seats`. New
York, Portland, and BT use lexicographic tie-breaking, while Scotland collects both lexicographic
and random variants. Alongside the six rules evaluated in New York and Portland, the Scottish and
BT recipes also include a random voting rule.

Random streams are seeded from the base seed and stable task identifiers, so changing the worker
count or resume order does not change them during BT collection and profile generation. The
runners also set `PYTHONHASHSEED=0`; use the same setting for standalone randomized computations.

For comparison with saved results, reuse the supplied BT profiles to keep the input sample fixed.
Their original generation seeds were not recorded, so a new sample should yield statistically
similar results without reproducing those specific profiles. Even with fixed inputs, exact
numerical agreement is not guaranteed because the saved results lack complete execution records.
The paper's reference result trees and final figure/table mappings have not yet been designated.

When combining BT result sets, their UM and IIA arrays must refer to the same profiles in the same
order because scores are paired by position.

## Additional analyses

### Scottish confidence intervals

After collecting Scottish scores, compute the interval CSVs before rendering bootstrap plots:

```sh
uv run --locked python code/pipelines/scottish/compute_bootstrap_intervals.py \
  --output-dir results/scottish-run --n-resamples 10000 --alpha 0.05 --seed 0
uv run --locked python code/pipelines/scottish/plots/plot_um_iia_bootstrap.py \
  --output-dir results/scottish-run
uv run --locked python code/pipelines/scottish/plots/plot_bootstrap_rectangles.py \
  --output-dir results/scottish-run
```

The explicit settings above match the defaults: 10,000 resamples, alpha 0.05, and seed 0. If you
want to overlay newly computed intervals on repository scores, select both sources by passing
`--stats-dir stats` and `--bootstrap-dir results/scottish-run/stats/scottish_stats/bootstrap` to
the overlay plotter.

### BT alpha distributions

Alpha comparisons use metric configurations beyond those computed by the main recipe. Once you
have the inputs described in the
[BT sensitivity plot guide](../code/archive/pipelines/bradley_terry/README.md), pool the saved
two-bloc scores and render the distributions:

```sh
uv run --locked python code/pipelines/bradley_terry/pool_alpha_metrics.py
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant worst_case
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant average
```

Pooling writes to `stats/bt_alpha_grouped/3_seats/`, with each group fixing the full
four-component alpha setting, total candidate count (8 or 10), and voting rule (Borda, STV, or
plurality). Within a group, raw scores are concatenated across candidate splits, bloc proportions,
and cohesion settings, so the resulting distributions compare alpha settings across the pooled
experiment grid. The pooler rejects incomplete grids, empty arrays, and unequal profile counts.

By default, the plotter writes to `code/archive/plots/bt_plots/alpha_boxplots/`. To keep both the
pooled scores and figures in a separate run, pass
`--bt-stats-dir stats/bt_2_bloc_profile_stats --output-dir results/alpha` to pooling, then
`--stats-dir results/alpha/stats --output-dir results/alpha` to plotting.

### BT proportionality

Proportionality calculations need matching `preference_dfs` utility files alongside the
`preference_profiles` directory, so the supplied profile archive alone is insufficient. Once both
inputs are available, use
[`compute_proportionality.py`](../code/pipelines/bradley_terry/compute_proportionality.py) to
collect the statistics and
[`plot_proportionality_waterfall.py`](../code/pipelines/bradley_terry/plots/plot_proportionality_waterfall.py)
to render the results. Both scripts expose their supported experiment settings through `--help`.

### Portland boost tables

Generate editable LaTeX boost matrices and PDF/PNG previews from the Portland profiles:

```sh
uv run --locked python code/pipelines/portland/plots/plot_boost_matrix.py --district all
uv run --script code/pipelines/portland/export_boost_tables.py --district all
```

The first command saves unrounded matrices, including candidate order and slate membership, to
`stats/portland_boost_matrices/`. The exporter then reads those matrices and writes
`TEX_<district>_boost_matrix` and `TEX_with_nums_<district>_boost_matrix` beneath
`plots/portland/boost_tables/`, producing `.tex`, `.pdf`, and `.png` files for D1 through D4.
Numbered versions display boosts to two decimal places in black or white text for contrast, with
undefined entries left blank in both versions.

Both versions follow the plotter's layout and styling: an 8-inch square matrix with the PRGn
colormap, bold sans-serif labels, and slate separators. Colors are computed from unrounded boosts
and saturate outside the selected limits, which default to -0.21 and 0.21. Read each entry as the
boost to the row candidate from the column candidate.

The exporter's inline dependency metadata tells uv to manage a separate environment for
GerryTools, whose NumPy requirements conflict with the locked VoteKit version. To render the
tables, you also need XeLaTeX or LuaLaTeX with `standalone`, `nicematrix`, TikZ, and `fontspec`,
the DejaVu Sans font, and Poppler for PNG export.

Use `--stats-dir` to read matrix CSVs from another location and `--output-dir` to save the TeX
sources and previews beneath a different run root. Running the exporter again replaces its
generated files, including any manual edits to the TeX sources.

### Portland diagnostics

For a clustering diagnostic, add `--diagnostics` to the Portland runner. Short-burst search uses a
seeded random stream and checks the stability of the score and partition across 1,000 restart
trials. These trials measure empirical stability without establishing global optimality.

When repeatedly editing boost figures, pass `--cache-dir results/boost-cache` to reuse computed
matrices. A cached matrix is used only when the input CSV contents, ordered focus candidates, and
VoteKit version match; without caching, the plotter computes it from the selected CSV each time.

## Generate a synthetic sample

To analyze a new BT sample, first generate the profiles and their paired preference interval
files, then create a folder list for the collector. The following commands complete that sequence
and save the metric results beneath the same run root:

```sh
PYTHONHASHSEED=0 uv run --locked python code/pipelines/bradley_terry/generate_profiles.py \
  --output-dir results/new-sample --seed 0 --n-jobs 4
uv run --locked python scripts/generate_settings.py \
  --profile-root results/new-sample/data/preference_profiles \
  --output code/config/new-sample-profiles.txt
./scripts/run_bt_pipeline.sh --settings-file code/config/new-sample-profiles.txt \
  --output-dir results/new-sample --seed 0 --n-jobs 4
```

The generator uses the experiment grid in `code/voting_metrics_main_code/constants.py` and skips a
sample if either its profile or paired interval file exists. To regenerate that sample, move both
files before rerunning generation.

The collector reads `code/config/bt_profiles.txt` unless `--settings-file` selects another list,
as in the example above. Folder paths in either list may be absolute or relative to the repository
root.
