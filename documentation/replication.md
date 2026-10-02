# Replication workflow

Use the dataset runners to compute fairness metrics and produce the main figures and tables.
The [pipeline index](../code/pipelines/README.md) lists individual analyses and their input
requirements. Run the commands below from the repository root, and use `--help` to inspect a
script's options.

- [Setup and inputs](#setup-and-inputs)
- [Run a dataset analysis](#run-a-dataset-analysis)
- [Output locations and saved results](#output-locations-and-saved-results)
- [Metrics and reproducibility](#metrics-and-reproducibility)
- [Additional analyses](#additional-analyses)
- [Generate a synthetic sample](#generate-a-synthetic-sample)

## Setup and inputs

Follow the [README setup instructions](../README.md#quick-start) to install uv, prepare the
environment, and run the checks.

NY and Portland analyses use the cleaned CSVs in `data/`. Scotland and Bradley–Terry (BT) require
additional inputs:

| Dataset | Input and source |
| ------- | ---------------- |
| NY | `data/NY_mayor_cleaned_votekit.csv`, prepared from the [2025 primary CVRs](https://www.vote.nyc/sites/default/files/pdf/election_results/2025/20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip) |
| Portland | `data/Portland_D[1-4]_cleaned_votekit.csv`, prepared from the [Portland Postmortem CVRs](https://github.com/mggg/Portland-Postmortem/tree/main/Restructured%20Repo/CVRs/raw_votekit_csv) |
| Scotland | `data/scot-elex/`, retrieved from [scot-elex](https://github.com/mggg/scot-elex) at the revision pinned by the fetcher |
| BT | `data/preference_profiles/`, extracted from the repository's `data/preference_profiles.tar.xz` archive |

Retrieve the optional inputs with:

```sh
uv run --locked python scripts/fetch_data.py scottish
git lfs pull --include=data/preference_profiles.tar.xz
uv run --locked python scripts/fetch_data.py bt
```

The BT archive is about 1.96 GB compressed. Fetching creates a complete new dataset directory
and refuses an existing destination. Use `--destination` to retrieve inputs elsewhere.

The runners use the cleaned NY and Portland files directly. Rebuilding them requires additional
preparation: the NY cleaner needs untracked `NY_mayor_all.csv`, and the Portland cleaner downloads
from a mutable upstream branch whose original revision was not recorded.

## Run a dataset analysis

Choose a separate output directory for a new computation:

```sh
./scripts/run_ny_pipeline.sh --output-dir results/ny-run
./scripts/run_portland_pipeline.sh --output-dir results/portland-run
./scripts/run_scottish_pipeline.sh --output-dir results/scottish-run --n-jobs 4
./scripts/run_bt_pipeline.sh --output-dir results/bt-run --n-jobs 4
```

By default, each runner computes scores and exports the outputs listed below.
Use `--mode stats` to compute scores alone or `--mode figures` to rebuild figures and tables from
saved scores. To inspect the commands before launching a potentially lengthy computation, add
`--dry-run`:

```sh
./scripts/run_portland_pipeline.sh --output-dir results/portland-run --dry-run
./scripts/run_bt_pipeline.sh --output-dir results/bt-run --mode figures
```

| Dataset | Statistics | Presentation outputs |
| ------- | ---------- | -------------------- |
| NY | `stats/ny_stats/` | `tables/ny.csv` |
| Portland | `stats/portland_stats/` | `tables/portland.csv`, `plots/portland/boost_matrix/` |
| Scotland | `stats/scottish_stats/` | `plots/scottish/`, `stats/scottish_stats/*limited.csv` |
| BT | `stats/bt_2_bloc_profile_stats/` | `plots/bt_plots/` |

These paths are relative to the selected output directory. The runners cover the main analyses,
and additional plotters remain available through the pipeline index. Full computations can take
many CPU-hours.

## Output locations and saved results

`--output-dir` selects a run root containing `stats/`, `plots/`, `tables/`, and generated `data/`
as needed. It defaults to the repository root. Figures mode reads statistics from that run root
unless an input directory is supplied explicitly.

| Option | Purpose | Default |
| ------ | ------- | ------- |
| `--data-dir` | Cleaned inputs and downloaded datasets | Repository `data/` |
| `--output-dir` | Run root for outputs | Repository root |
| `--stats-dir` | Parent of dataset statistics directories | `<output-dir>/stats/` |
| `--bt-stats-dir` | BT statistics tree containing seat-count directories | `<output-dir>/stats/bt_2_bloc_profile_stats/` |
| `--seed` | Base seed for collection or generation | `0` |
| `--n-jobs` | Parallel workers in supported workflows | `1` |

Relative paths resolve from the calling directory. Each script exposes the options relevant to
its analysis. For example, to plot repository statistics into a separate output directory:

```sh
uv run --locked python code/pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats \
  --output-dir results/figure-review
```

Collectors skip existing metric scores and election results. Profiles and their paired preference
interval files are also preserved. To recompute, use a new output directory or move the relevant
files manually. Skipping a result does not check whether its settings match the current run.
Figures, exported tables, bootstrap summaries, and settings files are overwritten on repeat runs.

## Metrics and reproducibility

The main recipes compute unanimity (UM) and independence of irrelevant alternatives (IIA) scores
for rankings and winner sets. UM uses worst-case aggregation and arcsin interpolation, while
IIA averages over single-candidate removals. In the paper, ranking metrics use rho and winner-set
metrics use sigma. The code names ranking metrics `sigma_UM` and `sigma_IIA`, with `_winner_set`
suffixes for winner-set metrics.

NY elects one candidate, Portland three, and Scotland uses the seat count in each input. The BT
recipe defaults to three seats, adjustable with `--n-seats`. NY, Portland, and BT
use lexicographic tie-breaking. Scotland collects both lexicographic and random variants. The
Scottish and BT recipes include the random voting rule in addition to the six rules used for NY
and Portland.

Seeds are derived from the base seed and stable task identifiers. For BT collection and profile
generation, worker count and resume order do not change the random streams. Runners set
`PYTHONHASHSEED=0`; set it likewise when launching standalone randomized computations.

Reuse the supplied BT profiles to keep the input sample fixed. Their original generation seeds
were not recorded, and generating a new sample should produce statistically similar results
without reproducing those specific profiles. Saved results also lack complete execution records,
so exact agreement with their numerical values is not guaranteed. The paper's reference result
trees and final figure/table mappings have not yet been designated.

BT UM and IIA score arrays are paired by position. When combining result sets, ensure they use
the same profiles in the same order.

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

The default calculation uses 10,000 resamples, alpha 0.05, and seed 0. To combine repository scores
with newly computed intervals, pass `--stats-dir stats` and
`--bootstrap-dir results/scottish-run/stats/scottish_stats/bootstrap` to the overlay plotter.

### BT alpha distributions

Alpha comparisons need more metric configurations than the main recipe computes. See the
[BT sensitivity plot guide](../code/archive/pipelines/bradley_terry/README.md) for the required
inputs, then pool the saved two-bloc scores before plotting:

```sh
uv run --locked python code/pipelines/bradley_terry/pool_alpha_metrics.py
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant worst_case
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant average
```

Pooling writes to `stats/bt_alpha_grouped/3_seats/`. Groups fix the full four-component alpha
setting, total candidate count (8 or 10), and voting rule (Borda, STV, or plurality). Within each
group, raw scores are concatenated across candidate splits, bloc proportions, and cohesion
settings. Interpret these distributions as comparisons over the pooled experiment grid.
Incomplete grids, empty arrays, and unequal profile counts are rejected.

The plotter writes to `code/archive/plots/bt_plots/alpha_boxplots/`. For a separate run, pass
`--bt-stats-dir stats/bt_2_bloc_profile_stats --output-dir results/alpha` to pooling and
`--stats-dir results/alpha/stats --output-dir results/alpha` to plotting.

### BT proportionality

Proportionality calculations require matching `preference_dfs` utility files alongside the
`preference_profiles` directory. Those files are not included in the supplied profile archive.
When both inputs are available, use
[`compute_proportionality.py`](../code/pipelines/bradley_terry/compute_proportionality.py) to
collect the statistics and
[`plot_proportionality_waterfall.py`](../code/pipelines/bradley_terry/plots/plot_proportionality_waterfall.py)
to render them. Inspect `--help` for the supported experiment settings.

### Portland boost tables

Generate editable LaTeX boost matrices and PDF/PNG previews from the Portland profiles:

```sh
uv run --locked python code/pipelines/portland/plots/plot_boost_matrix.py --district all
uv run --script code/pipelines/portland/export_boost_tables.py --district all
```

The plotter saves unrounded matrices with candidate order and slate membership to
`stats/portland_boost_matrices/`. Under `plots/portland/boost_tables/`, the table exporter
writes `TEX_<district>_boost_matrix` and `TEX_with_nums_<district>_boost_matrix` in `.tex`,
`.pdf`, and `.png` formats for D1 through D4. Numbered versions display boosts to two decimal
places, with black or white text for contrast. Undefined entries remain blank in both versions.

Both versions use the plotter's 8-inch square matrix, PRGn colormap, bold sans-serif labels,
and slate separators. Colors use unrounded boosts and saturate outside the selected limits
(default: -0.21 to 0.21). Rows identify the boosted candidate; columns identify the conditioning
candidate.

UV manages a separate environment for GerryTools automatically because its NumPy requirements
conflict with the locked VoteKit version. Rendering requires XeLaTeX or LuaLaTeX with
`standalone`, `nicematrix`, TikZ, and `fontspec`, the DejaVu Sans font, and Poppler for PNG
export. Use `--stats-dir` to select saved matrix CSVs and `--output-dir` to save renders under
another run root. Exports replace the generated files, including manual edits to the TeX sources.

### Portland diagnostics

Add `--diagnostics` to the Portland runner to execute clustering searches. Short-burst search
uses a seeded random stream and runs 1,000 restart trials to check stability of the score and
partition. These trials provide an empirical diagnostic, not a proof of global optimality, and
can be expensive.

For repeated boost-figure editing, the boost plotter accepts `--cache-dir results/boost-cache`.
It reuses matrices only when the input CSV contents, ordered focus candidates, and VoteKit
version match. Without that option, it computes the matrix from the selected CSV.

## Generate a synthetic sample

BT generation writes preference profiles and their paired preference interval files. Create a
sample, list its folders, and run the metrics with:

```sh
PYTHONHASHSEED=0 uv run --locked python code/pipelines/bradley_terry/generate_profiles.py \
  --output-dir results/new-sample --seed 0 --n-jobs 4
uv run --locked python scripts/generate_settings.py \
  --profile-root results/new-sample/data/preference_profiles \
  --output code/config/new-sample-profiles.txt
./scripts/run_bt_pipeline.sh --settings-file code/config/new-sample-profiles.txt \
  --output-dir results/new-sample --seed 0 --n-jobs 4
```

The experiment grid is defined in `code/voting_metrics_main_code/constants.py`. If either a
profile or its paired interval file exists, generation skips the pair. Move both files to
regenerate that sample.

The BT collector uses `code/config/bt_profiles.txt` by default. Entries in a settings file may
be absolute paths or paths relative to the repository root.
