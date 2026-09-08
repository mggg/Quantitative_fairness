# Replication workflow

## Scope and status

This package supports the four primary metrics: worst-case UM with arcsin interpolation and
average single-candidate IIA, each for rankings and winner sets. NY elects one candidate,
Portland and the maintained BT runner elect three, and Scotland uses the seat count in each input.
NY, Portland, and BT use lexicographic tie-breaking; Scotland collects lexicographic and random
variants. All seven voting rules run for BT and Scotland; NY and Portland run the six substantive
rules, as in their original collectors.

The publication reference directory and exact figure/table numbers still need author designation.
No result directory has been renamed, discarded, or declared to be the published truth merely
because its name includes `final`. The following inventory identifies runnable artifact families,
not a claim that every published result has been verified.

| Artifact family           | Inputs                                     | Computation                                                                                      | Generated artifact                                            |
| ------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| NY election metrics       | Checksummed NY cleaned CSV                 | `pipelines/new_york/collect_metrics.py`                                                          | `stats/ny_stats/`, `tables/ny.csv`                            |
| Portland election metrics | Four checksummed district CSVs             | `pipelines/portland/collect_metrics.py`                                                          | `stats/portland_stats/`, `tables/portland.csv`                |
| Scottish primary metrics  | Pinned `scot-elex` CSVs, 3–14 candidates   | `pipelines/scottish/collect_metrics.py`                                                          | `stats/scottish_stats/`                                       |
| Scottish comparisons      | Scottish primary statistics                | `plot_um_iia_scatter.py`, `export_metric_tables.py`                                              | `plots/scottish/`, limited CSVs under `stats/scottish_stats/` |
| BT primary metrics        | Folders listed in `config/bt_profiles.txt` | `pipelines/bradley_terry/collect_metrics.py`                                                     | `stats/bt_2_bloc_profile_stats/3_seats/`                      |
| BT comparisons            | Matching primary BT statistics             | `plot_um_iia_scatter.py`, `plot_candidate_count_boxplots.py`, `plot_bloc_proportion_boxplots.py` | `plots/bt_plots/`                                             |

In the local manuscript, ranking metrics use rho and winner-set metrics use sigma. The Python
names `sigma_IIA` and `sigma_UM` denote ranking metrics; names ending in `_winner_set` denote
winner-set metrics. Match the final manuscript's notation before assigning publication numbers.

## Install and check

Use Python 3.12 and uv. The checked-in lockfile records the dependency versions.

```sh
uv sync --locked
uv run --locked pytest
uv run --locked python scripts/smoke_test.py
```

`uv sync --locked` only synchronizes the environment. It does not download, extract, clean, or
regenerate data.
The smoke example uses a temporary synthetic profile and checks its numerical output.

## Shared settings

The [pipeline index](../pipelines/README.md) lists collectors, plotters, clustering analyses,
and their input requirements by dataset.

`voting_metrics_main_code/constants.py` defines shared voting-rule order, colors, labels, font
sizes, and the Bradley–Terry experiment grid. The profile generator and matching plotters import
the same grid; changing it affects both. The grid matches the preserved profile manifest in
`config/bt_profiles.txt`. Historical analyses with distinct palettes or rule order keep those
settings locally.

Runtime paths and random-seed handling live in `voting_metrics_main_code/replication.py`.
BT metric lists and sweep palettes remain in `pipelines/bradley_terry/plots/_metrics.py`
and `_palettes.py`, respectively.

## Inputs

NY and Portland cleaned CSVs are already tracked. Their SHA-256 checksums and the original code
revision are recorded in `baseline.json`; source locations are in `data_sources.json`.

Retrieve additional inputs only when needed:

```sh
uv run --locked python scripts/fetch_data.py scottish
git lfs pull --include=data/preference_profiles.tar.xz
uv run --locked python scripts/fetch_data.py bt
```

Fetch refuses an existing destination, including a symlink. BT extraction verifies the archive
checksum, extracts into a temporary sibling, and publishes a complete new directory. It never
merges into an existing profile tree. Existing partial inputs can be investigated or supplemented
at a separate `--destination`; they are not automatically repaired or replaced.

The Scottish revision is pinned to the local input checkout recorded during cleanup. The BT
archive is about 1.96 GB compressed. The existing local data tree was about 41 GB, including
additional archives and utility files. Full recomputation can require many CPU-hours; no reliable
runtime benchmark has yet been established. `--n-jobs` defaults to one to bound resource usage.

The historical cleaners remain in `other_files/`. The NY cleaner relies on an untracked
`NY_mayor_all.csv`, and the Portland cleaner retrieves a mutable upstream branch. Neither is part
of environment synchronization or the supported replication path. Reconstructing and validating
the original raw-to-clean transformation remains a provenance task; do not run those scripts
against the preserved CSVs. Input redistribution terms must be recorded separately from the
repository's code license before publication. Existing source links are not evidence of a
particular redistribution license.

## Recompute statistics and figures

```sh
./scripts/run_ny_pipeline.sh
./scripts/run_portland_pipeline.sh
./scripts/run_scottish_pipeline.sh --n-jobs 4
./scripts/run_bt_pipeline.sh --n-jobs 4
```

New artifacts go to `results/generated/`, with `stats/`, `plots/`, and `tables/` beneath it.
Existing top-level `data/`, `stats/`, and `plots/` remain intact. Output-directory validation rejects
paths overlapping the preserved research directories, including resolved symlink targets. Existing
symlinks nested anywhere in a selected output tree are rejected, even if their targets are benign.
The maintained entry points live under `scripts/`. Redundant root runners have been removed;
the original research runners are preserved in `archive/pre_cleanup/`.

Use `--mode stats` to compute without plotting, `--mode figures` to use existing statistics, and
`--output-dir /path/to/new-results` for a separate run. Repeated runs may replace generated tables
and plots. BT and Scottish collectors skip existing metric outputs. Use a new output directory
when changing inputs, code, seeds, or experiment definitions; existing historical outputs have no
complete execution provenance. Run manifests record the seed, interpreter, lock checksum and,
for BT, settings checksum. They are not certificates of provenance for old results.

```sh
./scripts/run_ny_pipeline.sh --mode figures --stats-dir stats
./scripts/run_scottish_pipeline.sh --mode figures --stats-dir stats
./scripts/run_bt_pipeline.sh --mode figures \
  --bt-stats-dir stats/bt_2_bloc_profile_stats_final_experiment
```

The last command selects an existing tree explicitly; it does not designate it as the publication
reference. Plotting expects the directory layout and matching four metrics produced by the BT
collector. Bootstrap, proportionality, broad sensitivity sweeps, and earlier plotting scripts
remain available as research analyses but are not automatically executed by the maintained runner.
Proportionality also needs the original matching `preference_dfs` utility files, which are not in
the tracked profile archive. Portland clustering is opt-in with `--diagnostics`.

Two Scottish plot-and-table exporters expect aggregate JSON files that the current collectors do
not produce: `plot_boxplots_and_tables.py` and the CSV stage of
`plot_boxplots_by_variant_and_tiebreak.py`. With the current statistics tree, they fail on
missing aggregate inputs. Use `plot_metric_boxplots.py` and `export_metric_tables.py` for
the current layout; the maintained Scottish runner already uses the latter for tables.

Standalone plotting scripts read the preserved `stats/` tree by default and write under
`results/generated/plots/`. Select different inputs explicitly with `QF_STATS_DIR` (the parent
of the dataset statistics directories) or `QF_BT_STATS_DIR` (the exact BT primary-metric tree).
`QF_RESULTS_DIR` changes the output root without changing the input selection. The maintained
runner selects its generated statistics explicitly in `--mode all`; `--mode figures` defaults
to preserved statistics. Relative command-line and environment paths resolve from the calling
directory, including when a shell runner is invoked from outside the repository.

```sh
uv run --locked python pipelines/bradley_terry/plots/plot_proportionality_waterfall.py
QF_STATS_DIR=results/new-run/stats QF_RESULTS_DIR=results/new-run \
  uv run --locked python pipelines/bradley_terry/plots/plot_proportionality_waterfall.py
```

Waterfall derives points from the selected JSON inputs each time; it no longer reads or writes
the old root-level `.waterfall_cache/`. Profile paths stored in those JSON files may point outside
the repository, provided they retain the candidate-count and experiment folder names.

Scottish bootstrap collection also separates preserved inputs from generated outputs. To plot
new bootstrap intervals alongside the preserved primary statistics, select the generated
bootstrap directory independently. Without `QF_BOOTSTRAP_DIR`, bootstrap plots read
`scottish_stats/bootstrap/` beneath `QF_STATS_DIR` (or the preserved `stats/` default).

```sh
uv run --locked python pipelines/scottish/compute_bootstrap_intervals.py
QF_BOOTSTRAP_DIR=results/generated/stats/scottish_stats/bootstrap \
  uv run --locked python pipelines/scottish/plots/plot_um_iia_bootstrap.py
QF_BOOTSTRAP_DIR=results/generated/stats/scottish_stats/bootstrap \
  uv run --locked python pipelines/scottish/plots/plot_bootstrap_rectangles.py
```

`config/bt_profiles.txt` retains the original selection and order with repository-relative paths.
Generate a new selection without overwriting the old file:

```sh
uv run --locked python scripts/generate_settings.py --output config/new-bt-profiles.txt
./scripts/run_bt_pipeline.sh --settings-file config/new-bt-profiles.txt \
  --output-dir results/new-run
```

To create a new synthetic sample, run the generator with a new output location. It refuses existing
profile or utility directories and never replaces the archived data:

```sh
QF_SEED=0 uv run --locked python pipelines/bradley_terry/generate_profiles.py \
  --output-dir results/new-sample/preference_profiles --n-jobs 4
uv run --locked python scripts/generate_settings.py \
  --profile-root results/new-sample/preference_profiles \
  --output config/new-sample-profiles.txt
```

Task seeds derive from the requested seed and stable task identifiers, so BT resume order and
worker scheduling do not choose the random stream. The launchers also set `PYTHONHASHSEED=0`.
The archived profiles were generated with seeded runs of an older code version. The current code
follows different random-number and execution paths, so regenerating profiles and rerunning the
analyses should produce statistically similar results, not exact historical matches, even when
using the same seed. A seed fixes a stream within an implementation; it does not fix the sequence
of draws or how the implementation uses them. The original seed values are not recorded in the
replication metadata collected here. Reusing the archived profiles fixes the input sample, while
randomized voting and metric calculations can still differ from their historical counterparts.
The consolidated random rule sorts candidates before shuffling, incorporating the root version's
existing reproducibility improvement. The package's UM input validation and useful docstrings are
retained. Baseline deterministic comparisons and the test suite guard against accidental changes.

## Preservation and release work

`baseline.json` records the starting revision, Git tree IDs for tracked artifacts, cleaned-input
checksums, and local file counts. A full before/after local file inventory is used during cleanup.
No data, statistics, figures, notebooks, or manuscript files are removed or relocated. Historical
code snapshots live in `archive/pre_cleanup/`; the maintained implementation is in
`voting_metrics_main_code/`. Import from that package directly; root import shims have been removed.

Before release, designate the final manuscript version and each reference result tree, fill in
figure/table numbers in the inventory, validate all final artifacts, record input permissions,
and add the final citation. `paper/` is an ignored independent Git checkout, so it does not ship
with this repository. `dev_files/` is also ignored and must be inspected for unique publication
analyses before deciding what to distribute. Archiving the many individual JSON results or
rewriting Git history is deliberately deferred; neither is required to make the workflow usable.
