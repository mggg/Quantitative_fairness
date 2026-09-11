# Pipeline index

For primary replication, use the [main pipeline index](../../pipelines/README.md). Archived BT
figures use the [individual plot commands](bradley_terry/README.md), not the copied dataset runner.
The other dataset entries below retain their original workflow descriptions.

| Dataset                  | Primary runner                                                    | Collector                                                    |
| ------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------ |
| New York                 | [`run_ny_pipeline.sh`](../scripts/run_ny_pipeline.sh)             | [`new_york/collect_metrics.py`](new_york/collect_metrics.py) |
| Portland                 | [`run_portland_pipeline.sh`](../scripts/run_portland_pipeline.sh) | [`portland/collect_metrics.py`](portland/collect_metrics.py) |
| Scotland                 | [`run_scottish_pipeline.sh`](../scripts/run_scottish_pipeline.sh) | [`scottish/collect_metrics.py`](scottish/collect_metrics.py) |
| Bradley–Terry, two blocs | [Individual plot commands](bradley_terry/README.md)               | Uses saved scores                                            |

The Portland runner also generates boost matrices. NY and Portland export tables through [`export_tables.py`](../scripts/export_tables.py).
The Scottish runner renders UM–IIA scatterplots and exports metric tables.

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

The Scottish plotters share [`_data.py`](scottish/plots/_data.py) for loading metric JSONs
by rule, candidate count, variant, and tiebreak.

## Bradley–Terry analyses

The archived BT pipeline has been reduced to plotters for the retained figure families, their
shared helpers, and alpha-score pooling. See [its index and commands](bradley_terry/README.md),
including the figures whose source remains in notebooks. Its plotters read saved
repository statistics and default to outputs under `archive/plots/`.

## Portland and cross-dataset analyses

| File                                                                             | Purpose                                                                                   |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| [`plot_boost_matrix.py`](portland/plots/plot_boost_matrix.py)                    | Focus-candidate heatmaps and a separate colorbar; select `--district` or `all`            |
| [`run_short_bursts.py`](portland/clustering/run_short_bursts.py)                 | Search for candidate clusters; `--show-viz` displays the partition                        |
| [`run_brute_force.py`](portland/clustering/run_brute_force.py)                   | Enumerate candidate partitions to check the clustering heuristic                          |
| [`modularity.py`](portland/clustering/modularity.py)                             | Shared clustering scores and search functions                                             |
| [`partition_visualization.py`](portland/clustering/partition_visualization.py)   | Plotting helpers for candidate partitions                                                 |
| [`plot_m_statistic_histograms.py`](cross_dataset/plot_m_statistic_histograms.py) | BT and Scottish histogram functions; direct execution renders BT at B-bloc proportion 0.7 |

The Portland runner executes clustering only with `--diagnostics`. These searches can be expensive.

## Running an individual plotter

From the repository root:

```sh
uv run --locked python pipelines/scottish/plots/plot_um_iia_scatter.py
uv run --locked python pipelines/portland/plots/plot_boost_matrix.py --district all
uv run --locked python archive/pipelines/bradley_terry/plots/plot_alpha_sweep.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats
```

In the main workflows, collectors and plotters default to `stats/` and `plots/`, respectively. Collectors skip
existing result files; move them manually before recomputing. Profile generation prints a message
and skips a sample if either its profile or preference interval dataframe exists. Move both files
before regenerating that pair. Figures, exported tables, and bootstrap summaries may overwrite
existing derived files.

Use `--stats-dir`, `--bt-stats-dir`, and `--bootstrap-dir` to select inputs and `--output-dir`
to choose a run root containing `stats/`, `plots/`, and `tables/`. Main-workflow inputs default to
the selected run root's statistics. Archived BT plotters instead read repository statistics and
write under `archive/plots/` by default; their input selection is independent of `--output-dir`. All executable workflows support `--help`; importing modules does not run
analyses. The [replication guide](../../docs/replication.md) contains ordered commands and prerequisites
for the primary recipes and additional analyses. `replicate.py --dry-run` prints its full recipe.

BT plotters expose `--n-seats` and share a selector in `_data.py` that reports the requested
experiment and matched files.
Boost plotting reads the requested CSV by default; `--cache-dir` enables content-matched caching.

Dataset directories use lowercase names; old `NY/` paths now live under `new_york/`.
