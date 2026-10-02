# Pipeline index

Start with the dataset runners in [`scripts/`](../../scripts) for the primary replication
workflow. Within each dataset, `collect_metrics.py` computes statistics, `plots/plot_*.py` renders
figures, and other filenames describe the computation or export they perform. The tables below
list the retained analyses; the runners execute only the primary subset indicated here.

| Dataset                  | Primary runner                                                       | Collector                                                              |
| ------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| New York                 | [`run_ny_pipeline.sh`](../../scripts/run_ny_pipeline.sh)             | [`new_york/collect_metrics.py`](new_york/collect_metrics.py)           |
| Portland                 | [`run_portland_pipeline.sh`](../../scripts/run_portland_pipeline.sh) | [`portland/collect_metrics.py`](portland/collect_metrics.py)           |
| Scotland                 | [`run_scottish_pipeline.sh`](../../scripts/run_scottish_pipeline.sh) | [`scottish/collect_metrics.py`](scottish/collect_metrics.py)           |
| Bradley–Terry, two blocs | [`run_bt_pipeline.sh`](../../scripts/run_bt_pipeline.sh)             | [`bradley_terry/collect_metrics.py`](bradley_terry/collect_metrics.py) |

The Portland runner also generates boost matrices. NY and Portland export tables through
[`export_tables.py`](../../scripts/export_tables.py). The Scottish runner renders UM–IIA
scatterplots and exports metric tables. The BT runner renders UM–IIA scatterplots. Supplementary
BT boxplots and sweeps are indexed in the
[archive guide](../archive/pipelines/bradley_terry/README.md).

## Scottish analyses

| File                                                                                                  | Purpose                                                                                |
| ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [`compute_bootstrap_intervals.py`](scottish/compute_bootstrap_intervals.py)                           | Compute confidence intervals and Bonferroni rectangles from metric JSONs               |
| [`export_metric_tables.py`](scottish/export_metric_tables.py)                                         | Export selected metrics to CSV; used by the runner                                     |
| [`plot_um_iia_scatter.py`](scottish/plots/plot_um_iia_scatter.py)                                     | UM–IIA comparisons for rankings and winner sets; used by the runner                    |
| [`plot_um_iia_bootstrap.py`](scottish/plots/plot_um_iia_bootstrap.py)                                 | Scatterplots with bootstrap means and confidence rectangles                            |
| [`plot_um_iia_percentiles.py`](scottish/plots/plot_um_iia_percentiles.py)                             | Percentile thresholds and means by voting rule                                         |
| [`plot_bootstrap_rectangles.py`](scottish/plots/plot_bootstrap_rectangles.py)                         | Standalone Bonferroni rectangle figures                                                |
| [`plot_metric_boxplots.py`](scottish/plots/plot_metric_boxplots.py)                                   | Consolidated metric boxplots and rule legend                                           |
| [`plot_boxplots_by_variant_and_tiebreak.py`](scottish/plots/plot_boxplots_by_variant_and_tiebreak.py) | Boxplots selected by `--variant` and `--tiebreak`, plus aggregate-table export         |
| [`plot_boxplots_and_tables.py`](scottish/plots/plot_boxplots_and_tables.py)                           | Six-rule boxplots and aggregate-table export, selected by `--variant` and `--tiebreak` |

The last two scripts also require aggregate `*stats.json` files that the primary collector does
not produce. Their CSV stage fails if those inputs are absent. Use `plot_metric_boxplots.py` and
`export_metric_tables.py` when working only with primary collector outputs. Bootstrap plotters
need the interval CSVs produced by `compute_bootstrap_intervals.py`.

The Scottish plotters share [`_data.py`](scottish/plots/_data.py) for loading metric JSONs by
rule, candidate count, variant, and tiebreak.

## Bradley–Terry analyses

The top-level BT collector reads the two-bloc folders listed in `code/config/bt_profiles.txt`.
`pool_alpha_metrics.py` pools those saved scores by full alpha tuple and total candidate count;
the [archived alpha plotter](../archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py)
renders the pooled distributions. Neither step reruns elections.

The individual-metric collectors share [`_metrics.py`](bradley_terry/_metrics.py) to bind metric
parameters. Metric settings distinguish UM interpolation from IIA aggregation.

| File                                                                                         | Purpose                                                                        |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [`generate_profiles.py`](bradley_terry/generate_profiles.py)                                 | Generate the two-bloc profile grid and matching utilities                      |
| [`collect_single_folder_metrics.py`](bradley_terry/collect_single_folder_metrics.py)         | Compute one selected metric for a two-bloc folder using `--input-folder`       |
| [`compute_proportionality.py`](bradley_terry/compute_proportionality.py)                     | Compute representation diagnostics using profiles and their utility files      |
| [`plot_um_iia_scatter.py`](bradley_terry/plots/plot_um_iia_scatter.py)                       | UM–IIA comparisons; used by the runner                                         |
| [`plot_um_mean_vs_variance.py`](bradley_terry/plots/plot_um_mean_vs_variance.py)             | UM mean versus variance, split by interpolation                                |
| [`plot_proportionality_waterfall.py`](bradley_terry/plots/plot_proportionality_waterfall.py) | Representation shortfalls from proportionality JSONs                           |
| [`pool_alpha_metrics.py`](bradley_terry/pool_alpha_metrics.py)                               | Pool saved BT scores into `stats/bt_alpha_grouped`, retaining source filenames |

BT plotting helpers are [`_metrics.py`](bradley_terry/plots/_metrics.py), which lists metric
selections, and [`_data.py`](bradley_terry/plots/_data.py), which loads arrays and summary points
in file order. They are imported by plotters and are not standalone commands. Archived broad
sweeps require more metric variants than the primary runner computes. See the
[replication guide](../../documentation/replication.md) for input layouts and limitations.

## Portland and cross-dataset analyses

| File                                                                             | Purpose                                                                                   |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [`plot_boost_matrix.py`](portland/plots/plot_boost_matrix.py)                    | Focus-candidate heatmaps and a separate colorbar; select `--district` or `all`            |
| [`export_boost_tables.py`](portland/export_boost_tables.py) | Colored boost tables with TeX sources and PDF/PNG renders; see the [guide](../../documentation/replication.md#portland-boost-tables) |
| [`run_short_bursts.py`](portland/clustering/run_short_bursts.py)                 | Search for candidate clusters; `--show-viz` displays the partition                        |
| [`run_brute_force.py`](portland/clustering/run_brute_force.py)                   | Enumerate candidate partitions to check the clustering heuristic                          |
| [`modularity.py`](portland/clustering/modularity.py)                             | Shared clustering scores and search functions                                             |
| [`partition_visualization.py`](portland/clustering/partition_visualization.py)   | Plotting helpers for candidate partitions                                                 |
| [`plot_m_statistic_histograms.py`](cross_dataset/plot_m_statistic_histograms.py) | BT and Scottish histogram functions; direct execution renders BT at B-bloc proportion 0.7 |

The clustering workflows share [`load_profile.py`](portland/clustering/load_profile.py) for
profile loading and viable-candidate projection. Short-burst search and restart verification are
separate operations; the CLI runs both.

The Portland runner executes clustering only with `--diagnostics`. These searches can be
expensive.

## Running an individual plotter

From the repository root:

```sh
uv run --locked python code/pipelines/scottish/plots/plot_um_iia_scatter.py
uv run --locked python code/pipelines/portland/plots/plot_boost_matrix.py --district all
uv run --locked python code/pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats
```

Standalone collectors and plotters default to `stats/` and `plots/`, respectively. Collectors skip
existing result files; move them manually before recomputing. Profile generation prints a message
and skips a sample if either its profile or preference interval dataframe exists. Move both files
before regenerating that pair. Figures, exported tables, and bootstrap summaries may overwrite
existing derived files.

Use `--stats-dir`, `--bt-stats-dir`, and `--bootstrap-dir` to select inputs and `--output-dir` to
choose a run root containing `stats/`, `plots/`, and `tables/`. Inputs default to the selected run
root's statistics. All executable workflows support `--help`; importing modules does not run
analyses. The [replication guide](../../documentation/replication.md) contains ordered commands
and prerequisites for the primary recipes and additional analyses. `replicate.py --dry-run` prints
its full recipe.

BT plotters expose `--n-seats`. Boost plotting reads the requested CSV by default; `--cache-dir`
enables content-matched caching.
