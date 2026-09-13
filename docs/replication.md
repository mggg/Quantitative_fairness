# Replication workflow

## Start with an artifact

Use the [pipeline index](../pipelines/README.md) to locate a figure or analysis. Each executable
workflow accepts `--help`. The commands below are ordinary Python scripts; each prints its selected
paths, and the dataset runner prints every command before executing it.

The publication reference tree and exact figure/table numbers still need author designation.
Directories containing `final` in their names are not automatically publication references.

| Artifact                            | Computation                                                                                                                             | Inputs                             | Output beneath the run root                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| NY metrics and table                | `pipelines/new_york/collect_metrics.py`, `scripts/export_tables.py ny`                                                                  | Cleaned NY CSV                     | `stats/ny_stats/`, `tables/ny.csv`                     |
| Portland metrics and table          | `pipelines/portland/collect_metrics.py`, `scripts/export_tables.py portland`                                                            | Four cleaned district CSVs         | `stats/portland_stats/`, `tables/portland.csv`         |
| Portland boost matrices             | `pipelines/portland/plots/plot_boost_matrix.py --district all`                                                                          | Cleaned district CSVs              | `plots/portland/boost_matrix/`                         |
| Scottish metrics                    | `pipelines/scottish/collect_metrics.py`                                                                                                 | Pinned `scot-elex` CSVs            | `stats/scottish_stats/`                                |
| Scottish primary figures and tables | `pipelines/scottish/plots/plot_um_iia_scatter.py`, `pipelines/scottish/export_metric_tables.py`                                         | Scottish metric JSONs              | `plots/scottish/`, `stats/scottish_stats/*limited.csv` |
| BT metrics                          | `pipelines/bradley_terry/collect_metrics.py`                                                                                            | Profile folders in a settings file | `stats/bt_2_bloc_profile_stats/`                       |
| BT primary figures                  | `pipelines/bradley_terry/plots/plot_um_iia_scatter.py` | Matching BT metric JSONs           | `plots/bt_plots/`                                      |

The primary recipes compute worst-case UM with arcsin interpolation and average single-candidate
IIA, for rankings and winner sets. NY elects one candidate, Portland three, and Scotland uses the
seat count in each input. BT defaults to three seats and exposes `--n-seats` in both collection
and plotting. NY, Portland, and BT use lexicographic tie-breaking; Scotland collects lexicographic
and random variants. BT and Scotland run seven rules; NY and Portland run six substantive rules.

In the local manuscript, ranking metrics use rho and winner-set metrics use sigma. The Python
names `sigma_IIA` and `sigma_UM` denote ranking metrics; `_winner_set` names denote winner-set metrics.

## Install and inspect

Use Python 3.12 and uv. The lockfile fixes the environment.

```sh
uv sync --locked
uv run --locked pytest
uv run --locked python scripts/smoke_test.py
uv run --locked python scripts/replicate.py portland --dry-run
```

Synchronization does not retrieve, extract, clean, or regenerate data. The smoke example writes
only temporary synthetic inputs and checks all four metric outputs. A dry run prints the complete
recipe without writing files or requiring its data to be present. Printed commands include the
project location and process settings, so they can be copied into a terminal from another directory.

## Paths and saved results

`--output-dir` always names a **run root**, with `stats/`, `plots/`, `tables/`, and generated
`data/` beneath it as applicable. It defaults to the repository root, for both individual analyses
and dataset recipes. This preserves the familiar `stats/` and `plots/` locations.

In the code, `ROOT` is the only shared path constant. Workflow entry points derive their
directories directly with `Path` joins, such as `ROOT / "data"` or
`output_root / "stats/bt_2_bloc_profile_stats"`. Helpers receive the selected paths explicitly;
they do not choose a separate default input or output tree. When calling a helper from Python,
pass its required path arguments. The command-line defaults and options are unchanged.

| Option            | Meaning                                                          | Default                                                |
| ----------------- | ---------------------------------------------------------------- | ------------------------------------------------------ |
| `--data-dir`      | Directory containing cleaned inputs and downloaded input trees   | Repository `data/`                                     |
| `--output-dir`    | Run root for new outputs                                         | Repository root                                        |
| `--stats-dir`     | Parent of dataset statistics directories                         | `<output-dir>/stats/`                                  |
| `--bt-stats-dir`  | Exact two-bloc BT result tree, containing seat-count directories | `<output-dir>/stats/bt_2_bloc_profile_stats/`          |
| `--bootstrap-dir` | Exact directory of Scottish bootstrap interval CSVs              | Selected statistics root's `scottish_stats/bootstrap/` |
| `--seed`          | Base seed for collection or generation                           | `0`                                                    |
| `--n-jobs`        | Parallel workers in workflows that support parallelism           | `1`                                                    |

Only relevant options appear in each workflow's help. The runner derives its default BT tree
from the selected `--stats-dir`; bootstrap-only plotters derive their default interval directory
from the run root. Relative options resolve from the calling directory.

For a new computation, choose a new run root. Figures mode reads that run's statistics by default:

```sh
./scripts/run_bt_pipeline.sh --output-dir results/new-run --n-jobs 4 --seed 42
./scripts/run_bt_pipeline.sh --mode figures --output-dir results/new-run
uv run --locked python pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --output-dir results/new-run
```

To plot preserved results into a different output location, select the input explicitly:

```sh
uv run --locked python pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats_final_experiment \
  --output-dir results/figure-review
```

Preference profiles, preference interval dataframes, metric scores, and election results are
never replaced. Move an existing file manually before recomputing it; there is no force option.
Collectors skip completed results before doing expensive work. The shared writer publishes only
complete files and refuses a destination created concurrently by another process.

Figures, exported tables, bootstrap summaries, and settings files overwrite by default.
Existing historical results do not have complete execution provenance, and skipping a result
does not validate it against the current experiment.

## Dataset recipes and individual commands

```sh
./scripts/run_ny_pipeline.sh --output-dir results/ny-run
./scripts/run_portland_pipeline.sh --output-dir results/portland-run
./scripts/run_scottish_pipeline.sh --output-dir results/scottish-run --n-jobs 4
./scripts/run_bt_pipeline.sh --output-dir results/bt-run --n-jobs 4
```

`--mode stats` computes scores; `--mode figures` refreshes primary presentation artifacts;
`--mode all` performs both stages of the primary recipe. Portland includes boost plots.
The runner is an optional command recipe: individual scripts take the same explicit arguments.
It does not run every exploratory plot. Full runs can take many CPU-hours; there is no reliable
runtime benchmark yet. Inspect `--dry-run` before launching a full computation.

BT result filenames retain the existing experiment layout. Plotters use one shared selector for
metric, aggregation, interpolation, seats, voting rule, candidate counts, bloc proportions,
Dirichlet parameters, and cohesion. It prints the selection and matching file count. Missing
experiments raise an error identifying the exact requested files rather than producing empty plots.
Paired UM/IIA loading also checks that the two score arrays have the same length; the historical
format still assumes their observations have matching profile order.

## Additional analyses and prerequisites

Scottish bootstrap plots require interval CSVs as well as primary metric JSONs. Their numerical
settings are explicit: 10,000 resamples, alpha 0.05, seed 0 by default.

```sh
uv run --locked python pipelines/scottish/compute_bootstrap_intervals.py \
  --output-dir results/scottish-run --n-resamples 10000 --alpha 0.05 --seed 0
uv run --locked python pipelines/scottish/plots/plot_um_iia_bootstrap.py \
  --output-dir results/scottish-run
uv run --locked python pipelines/scottish/plots/plot_bootstrap_rectangles.py \
  --output-dir results/scottish-run
```

Use `--stats-dir stats --bootstrap-dir results/scottish-run/stats/scottish_stats/bootstrap`
on the overlay plotter when combining preserved primary scores with new interval CSVs.

BT proportionality requires matching `preference_dfs` utility files alongside `preference_profiles`.
Those utilities are not in the tracked profile archive. The collector exposes the candidate counts,
bloc proportion, and cohesion in `--help`; its output feeds `plot_proportionality_waterfall.py`.
The [archived BT sensitivity plots](../archive/pipelines/bradley_terry/README.md) require more
metric variants than the primary recipe computes.
`collect_single_folder_metrics.py` exposes the individual metric and variant choices.
Alpha boxplots use pooled copies of the saved two-bloc scores:

```sh
uv run --locked python pipelines/bradley_terry/pool_alpha_metrics.py
uv run --locked python archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant worst_case
uv run --locked python archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant average
```

Pooling writes twelve JSON files under `stats/bt_alpha_grouped/3_seats/`. Each file fixes the metric,
variant, interpolation, and tie-breaking method. Its groups retain the full four-component alpha
setting, total candidate count (8 or 10), and rule (Borda, STV, or plurality). Within a group, scores
are concatenated across the three candidate splits, five bloc proportions, and four cohesion
settings. With the supplied results, each group has 6,000 raw profile scores from 60 source files;
no means are substituted for observations. Each group lists its source paths relative to the BT
statistics root. Incomplete grids, empty arrays, and unequal profile counts raise an error.

The archived plotter defaults to `archive/plots/bt_plots/alpha_boxplots/`. These are distributions over the available
experiment grid, not estimates of alpha effects with all other parameters fixed. The three rules
have scores for every included metric configuration. Subset IIA is excluded because those scores
are absent. The old scalar-alpha grid (including 1/3 and 3, with 6–9 candidates) is not recreated.

For a separate run, pass `--bt-stats-dir stats/bt_2_bloc_profile_stats --output-dir results/alpha`
to pooling and `--stats-dir results/alpha/stats --output-dir results/alpha` to plotting. Both commands default to three seats and
lexicographic tie-breaking. Pooled score files are preserved on repeat runs; move them manually to
rebuild them. Figures overwrite by default. The original BT scores are only read.

The Scottish `plot_boxplots_and_tables.py` and the CSV stage of
`plot_boxplots_by_variant_and_tiebreak.py` require aggregate `*stats.json` inputs that the primary
collector does not produce. Use `plot_metric_boxplots.py` and `export_metric_tables.py` for primary
collector outputs. These alternative plots remain independently runnable for artifact selection.

Portland clustering is available separately, or through the Portland recipe's `--diagnostics`.
Short-burst initialization and proposals use one local seeded random stream. This makes the search
repeatable independently of NumPy's global random state, but changes draws from older versions that
mixed two random streams. The CLI separately runs 1,000 restart trials to check that the score and
partition remain stable up to cluster-label permutation; this is not a proof of global optimality.
It can be expensive. Boost plotting computes from the selected CSV by default. To speed repeated
font/layout adjustments, pass `--cache-dir results/boost-cache`. Cache keys include the CSV contents,
ordered focus candidates, and VoteKit version. A missing input is an error even if a cache exists.
The old district-only `.boost_cache/` files are retained but are not consulted.

## Inputs and synthetic samples

NY and Portland cleaned CSVs are tracked. Checksums and the original code revision are in
[`baseline.json`](baseline.json); source locations are in [`data_sources.json`](data_sources.json).
Retrieve optional inputs with:

```sh
uv run --locked python scripts/fetch_data.py scottish
git lfs pull --include=data/preference_profiles.tar.xz
uv run --locked python scripts/fetch_data.py bt
```

Fetching refuses existing destinations, including symlinks. BT extraction verifies the archive
checksum and publishes a complete new directory; it does not merge into a partially populated tree.
The Scottish revision is pinned. The BT archive is about 1.96 GB compressed; the local research
data tree included additional archives and utilities and was about 41 GB during the inventory.

`config/bt_profiles.txt` preserves the original folder selection and order. Its relative entries
resolve against the repository root. A new synthetic sample and selection can be created with:

```sh
PYTHONHASHSEED=0 uv run --locked python pipelines/bradley_terry/generate_profiles.py \
  --output-dir results/new-sample --seed 0 --n-jobs 4
uv run --locked python scripts/generate_settings.py \
  --profile-root results/new-sample/data/preference_profiles \
  --output config/new-sample-profiles.txt
./scripts/run_bt_pipeline.sh --settings-file config/new-sample-profiles.txt \
  --output-dir results/new-sample --seed 0 --n-jobs 4
```

The generator and sweep plotters share the experiment grid in
`voting_metrics_main_code/constants.py`. Changing the grid affects both. If either a profile or its
paired interval dataframe exists, generation prints a message and skips that sample, then continues
with the remaining samples. Move both files manually before regenerating the pair.

## Reproducibility and release status

Task seeds are passed explicitly and derived from stable task identifiers. Primary collectors and
profile generation are checked for repeatability; BT worker count and resume order do not choose
random streams. Recipes set `PYTHONHASHSEED=0`; set it likewise when launching standalone randomized
computations. Clustering retains its separate research algorithm and is not covered by the BT
worker-count guarantee.

The archived profiles were seeded with an older code version. This version follows different
random-number and execution paths, so regeneration should produce statistically similar results,
not exactly the same profiles or numerical values. Original seed values are not recorded in the
replication metadata. Reusing archived profiles fixes the sample, while randomized election and
metric calculations may still differ from historical runs.

The historical cleaners in `other_files/` have additional provenance requirements: the NY cleaner
needs untracked `NY_mayor_all.csv`, and the Portland cleaner retrieves a mutable upstream branch.
They are not part of the supported replication recipe. Raw-to-clean validation and input
redistribution permissions remain release tasks.

Before publication, designate the final manuscript, reference result trees, figure/table numbers,
and citation; validate the selected artifacts and record input permissions. The ignored `paper/`
and `dev_files/` material does not ship in a clone. Source snapshots remain under `archive/`;
research inputs, stored results, and notebooks are preserved.

## Changes from the earlier commands

Runtime `QF_*` environment overrides have been replaced by explicit CLI options. Use the table
above to translate old commands. `--output-dir` now means the run root in every analysis, including
boost plotting and profile generation; it is not the exact figure or profile directory.
The default recipe output root is now the repository, matching standalone scripts.
The former `alpha_sweep/plot_metric_boxplots.py` is preserved as
`archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py` and reads pooled two-bloc scores. The single-alpha collector is preserved as source text under
`archive/single_alpha/`; it required profile folders that are not supplied.
