# Pipeline index

The dataset runners in [`scripts/`](../../scripts) collect scores and produce the main outputs for
each dataset. Use this index to find the underlying computations or choose an additional
analysis: `collect_metrics.py` computes statistics, while scripts in `plots/` render figures from
saved results. The tables below identify which analyses the runners include.

| Dataset                  | Primary runner                                                       | Collector                                                              |
| ------------------------ | -------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| New York                 | [`run_ny_pipeline.sh`](../../scripts/run_ny_pipeline.sh)             | [`new_york/collect_metrics.py`](new_york/collect_metrics.py)           |
| Portland                 | [`run_portland_pipeline.sh`](../../scripts/run_portland_pipeline.sh) | [`portland/collect_metrics.py`](portland/collect_metrics.py)           |
| Scotland                 | [`run_scottish_pipeline.sh`](../../scripts/run_scottish_pipeline.sh) | [`scottish/collect_metrics.py`](scottish/collect_metrics.py)           |
| Bradley–Terry, two blocs | [`run_bt_pipeline.sh`](../../scripts/run_bt_pipeline.sh)             | [`bradley_terry/collect_metrics.py`](bradley_terry/collect_metrics.py) |

After collection, the New York and Portland runners export summary tables through
[`export_tables.py`](../../scripts/export_tables.py), and Portland also renders boost matrices.
Scotland and BT produce UM–IIA scatterplots, with metric tables included in the Scottish workflow.
For supplementary BT boxplots and parameter sweeps, see the
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

When working with the primary collector's outputs, use `plot_metric_boxplots.py` for boxplots and
`export_metric_tables.py` for tables. The last two scripts in the index need additional aggregate
`*stats.json` files, and their CSV export fails without those inputs. Bootstrap figures have a
separate prerequisite: run `compute_bootstrap_intervals.py` to produce their interval CSVs before
plotting.

For changes to Scottish data loading, start with [`_data.py`](scottish/plots/_data.py), which the
plotters share to select metric JSONs by voting rule, candidate count, variant, and tiebreak.

## Bradley–Terry analyses

The BT collector analyzes the two-bloc profile folders listed in `code/config/bt_profiles.txt`. To
compare alpha settings using saved results, `pool_alpha_metrics.py` groups scores by the full
alpha tuple and total candidate count, after which the
[archived alpha plotter](../archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py) renders
the distributions. These steps reuse the scores without rerunning elections.

| File                                                                                         | Purpose                                                                        |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [`generate_profiles.py`](bradley_terry/generate_profiles.py)                                 | Generate the two-bloc profile grid and matching utilities                      |
| [`collect_single_folder_metrics.py`](bradley_terry/collect_single_folder_metrics.py)         | Compute one selected metric for a two-bloc folder using `--input-folder`       |
| [`compute_proportionality.py`](bradley_terry/compute_proportionality.py)                     | Compute representation diagnostics using profiles and their utility files      |
| [`plot_um_iia_scatter.py`](bradley_terry/plots/plot_um_iia_scatter.py)                       | UM–IIA comparisons; used by the runner                                         |
| [`plot_um_mean_vs_variance.py`](bradley_terry/plots/plot_um_mean_vs_variance.py)             | UM mean versus variance, split by interpolation                                |
| [`plot_proportionality_waterfall.py`](bradley_terry/plots/plot_proportionality_waterfall.py) | Representation shortfalls from proportionality JSONs                           |
| [`pool_alpha_metrics.py`](bradley_terry/pool_alpha_metrics.py)                               | Pool saved BT scores into `stats/bt_alpha_grouped`, retaining source filenames |

The collectors share [`_metrics.py`](bradley_terry/_metrics.py) to bind their parameters, keeping
UM interpolation distinct from IIA aggregation. Plotters use their own
[`_metrics.py`](bradley_terry/plots/_metrics.py) for metric selections and
[`_data.py`](bradley_terry/plots/_data.py) to load arrays and summary points in file order. These
helpers are imported by the workflows rather than run as commands.

Broader parameter sweeps in the archive require metric variants beyond those computed by the
primary runner. Consult the [replication guide](../../documentation/replication.md) for their
input layouts and limitations before choosing an analysis.

## Portland and cross-dataset analyses

| File                                                                             | Purpose                                                                                                                              |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| [`plot_boost_matrix.py`](portland/plots/plot_boost_matrix.py)                    | Focus-candidate heatmaps and a separate colorbar; select `--district` or `all`                                                       |
| [`export_boost_tables.py`](portland/export_boost_tables.py)                      | Colored boost tables with TeX sources and PDF/PNG renders; see the [guide](../../documentation/replication.md#portland-boost-tables) |
| [`run_short_bursts.py`](portland/clustering/run_short_bursts.py)                 | Search for candidate clusters; `--show-viz` displays the partition                                                                   |
| [`run_brute_force.py`](portland/clustering/run_brute_force.py)                   | Enumerate candidate partitions to check the clustering heuristic                                                                     |
| [`modularity.py`](portland/clustering/modularity.py)                             | Shared clustering scores and search functions                                                                                        |
| [`partition_visualization.py`](portland/clustering/partition_visualization.py)   | Plotting helpers for candidate partitions                                                                                            |
| [`plot_m_statistic_histograms.py`](cross_dataset/plot_m_statistic_histograms.py) | BT and Scottish histogram functions; direct execution renders BT at B-bloc proportion 0.7                                            |

Portland's clustering workflows load profiles and project them onto viable candidates through
[`load_profile.py`](portland/clustering/load_profile.py). The short-burst CLI searches for a
partition and then checks its stability across restarts. Pass `--diagnostics` to include the
clustering analyses in the Portland dataset run.

## Running an individual plotter

Run individual analyses from the repository root. For example:

```sh
uv run --locked python code/pipelines/scottish/plots/plot_um_iia_scatter.py
uv run --locked python code/pipelines/portland/plots/plot_boost_matrix.py --district all
uv run --locked python code/pipelines/bradley_terry/plots/plot_um_iia_scatter.py \
  --bt-stats-dir stats/bt_2_bloc_profile_stats
```

By default, collectors write beneath `stats/` and plotters beneath `plots/`. Set `--output-dir` to
keep a run's `stats/`, `plots/`, and `tables/` together elsewhere, with its statistics becoming
the default plotting inputs. To read saved results from another location, use the relevant
`--stats-dir`, `--bt-stats-dir`, or `--bootstrap-dir` option. BT plotters also accept `--n-seats`,
while boost plotting reads the requested CSV unless `--cache-dir` enables content-matched caching.

Collection preserves existing results, so use a new output directory or move the saved files to
recompute them. Profile generation similarly skips a sample if either its profile or preference
interval dataframe exists, so both files must be moved to regenerate that pair. Figures, exported
tables, and bootstrap summaries may be overwritten on repeat runs.
