# Pipeline index

Start with the dataset runners in [`scripts/`](../scripts) for the primary replication workflow.
Within each dataset, `collect_metrics.py` computes statistics, `plots/plot_*.py` renders figures,
and other filenames describe the computation or export they perform. The tables below list the
retained analyses; the runners execute only the primary subset indicated here.

| Dataset | Primary runner | Collector |
| --- | --- | --- |
| New York | [`run_ny_pipeline.sh`](../scripts/run_ny_pipeline.sh) | [`new_york/collect_metrics.py`](new_york/collect_metrics.py) |
| Portland | [`run_portland_pipeline.sh`](../scripts/run_portland_pipeline.sh) | [`portland/collect_metrics.py`](portland/collect_metrics.py) |
| Scotland | [`run_scottish_pipeline.sh`](../scripts/run_scottish_pipeline.sh) | [`scottish/collect_metrics.py`](scottish/collect_metrics.py) |
| Bradley–Terry, two blocs | [`run_bt_pipeline.sh`](../scripts/run_bt_pipeline.sh) | [`bradley_terry/collect_metrics.py`](bradley_terry/collect_metrics.py) |

The NY and Portland runners export tables through [`export_tables.py`](../scripts/export_tables.py).
The Scottish runner renders UM–IIA scatterplots and exports metric tables. The BT runner renders
UM–IIA scatterplots plus candidate-count and bloc-proportion boxplots.

## Scottish analyses

| File | Purpose |
| --- | --- |
| [`compute_bootstrap_intervals.py`](scottish/compute_bootstrap_intervals.py) | Compute confidence intervals and Bonferroni rectangles from metric JSONs |
| [`export_metric_tables.py`](scottish/export_metric_tables.py) | Export selected metrics to CSV; used by the runner |
| [`plot_um_iia_scatter.py`](scottish/plots/plot_um_iia_scatter.py) | UM–IIA comparisons for rankings and winner sets; used by the runner |
| [`plot_um_iia_bootstrap.py`](scottish/plots/plot_um_iia_bootstrap.py) | Scatterplots with bootstrap means and confidence rectangles |
| [`plot_um_iia_percentiles.py`](scottish/plots/plot_um_iia_percentiles.py) | Percentile thresholds and means by voting rule |
| [`plot_bootstrap_rectangles.py`](scottish/plots/plot_bootstrap_rectangles.py) | Standalone Bonferroni rectangle figures |
| [`plot_metric_boxplots.py`](scottish/plots/plot_metric_boxplots.py) | Consolidated metric boxplots and rule legend |
| [`plot_boxplots_by_variant_and_tiebreak.py`](scottish/plots/plot_boxplots_by_variant_and_tiebreak.py) | Boxplots selected by `--variant` and `--tiebreak`, plus aggregate-table export |
| [`plot_boxplots_and_tables.py`](scottish/plots/plot_boxplots_and_tables.py) | Six-rule boxplots and aggregate-table export, selected by `--variant` and `--tiebreak` |

The last two scripts also require aggregate `*stats.json` files that the primary collector does
not produce. Their CSV stage fails if those inputs are absent. Use `plot_metric_boxplots.py` and
`export_metric_tables.py` when working only with primary collector outputs. Bootstrap plotters
need the interval CSVs produced by `compute_bootstrap_intervals.py`.

## Bradley–Terry analyses

The top-level BT collector reads the two-bloc folders listed in `config/bt_profiles.txt`.
`alpha_sweep/` contains the separate experiment with one alpha parameter per profile folder.
The two layouts are different inputs, even though both have plots involving alpha.

| File | Purpose |
| --- | --- |
| [`generate_profiles.py`](bradley_terry/generate_profiles.py) | Generate the two-bloc profile grid and matching utilities |
| [`collect_single_folder_metrics.py`](bradley_terry/collect_single_folder_metrics.py) | Compute one selected metric for a two-bloc folder using `--input-folder` |
| [`compute_proportionality.py`](bradley_terry/compute_proportionality.py) | Compute representation diagnostics using profiles and their utility files |
| [`plot_um_iia_scatter.py`](bradley_terry/plots/plot_um_iia_scatter.py) | UM–IIA comparisons; used by the runner |
| [`plot_candidate_count_boxplots.py`](bradley_terry/plots/plot_candidate_count_boxplots.py) | Metric distributions across candidate counts; used by the runner |
| [`plot_bloc_proportion_boxplots.py`](bradley_terry/plots/plot_bloc_proportion_boxplots.py) | Metric distributions across bloc proportions; used by the runner |
| [`plot_alpha_sweep.py`](bradley_terry/plots/plot_alpha_sweep.py) | Mean versus standard deviation, colored by the two-bloc alpha combinations |
| [`plot_cohesion_sweep.py`](bradley_terry/plots/plot_cohesion_sweep.py) | Mean versus standard deviation, colored by cohesion |
| [`plot_candidate_count_sweep.py`](bradley_terry/plots/plot_candidate_count_sweep.py) | Mean versus standard deviation, colored by candidate counts |
| [`plot_bloc_proportion_sweep.py`](bradley_terry/plots/plot_bloc_proportion_sweep.py) | Mean versus standard deviation, colored by bloc proportion |
| [`plot_iia_by_rule.py`](bradley_terry/plots/plot_iia_by_rule.py) | IIA mean versus standard deviation, colored by voting rule |
| [`plot_um_by_rule.py`](bradley_terry/plots/plot_um_by_rule.py) | UM mean versus standard deviation, colored by voting rule |
| [`plot_mean_vs_standard_deviation.py`](bradley_terry/plots/plot_mean_vs_standard_deviation.py) | Metric and interpolation comparisons |
| [`plot_um_mean_vs_variance.py`](bradley_terry/plots/plot_um_mean_vs_variance.py) | UM mean versus variance, split by interpolation |
| [`plot_proportionality_waterfall.py`](bradley_terry/plots/plot_proportionality_waterfall.py) | Representation shortfalls from proportionality JSONs |
| [`alpha_sweep/collect_metrics.py`](bradley_terry/alpha_sweep/collect_metrics.py) | Compute a selected metric from candidate-count/alpha folders |
| [`alpha_sweep/collect_metrics_borda_tiebreak.py`](bradley_terry/alpha_sweep/collect_metrics_borda_tiebreak.py) | Alternate alpha-sweep CLI that also offers Borda tie-breaking |
| [`alpha_sweep/plot_metric_boxplots.py`](bradley_terry/alpha_sweep/plot_metric_boxplots.py) | Boxplots from `bt_profile_stats`, selected by seats, variant, and tie-breaking |

BT plotting helpers are [`_metrics.py`](bradley_terry/plots/_metrics.py),
[`_palettes.py`](bradley_terry/plots/_palettes.py), and
[`_data.py`](bradley_terry/plots/_data.py), which loads arrays and summary points in file order.
They are imported by plotters and are not
standalone commands. The broad sweeps require more metric variants than the primary runner
computes. See the [replication guide](../docs/replication.md) for input layouts and limitations.

## Portland and cross-dataset analyses

| File | Purpose |
| --- | --- |
| [`plot_boost_matrix.py`](portland/plots/plot_boost_matrix.py) | Focus-candidate heatmaps and a separate colorbar; select `--district` or `all` |
| [`run_short_bursts.py`](portland/clustering/run_short_bursts.py) | Search for candidate clusters; `--show-viz` displays the partition |
| [`run_brute_force.py`](portland/clustering/run_brute_force.py) | Enumerate candidate partitions to check the clustering heuristic |
| [`modularity.py`](portland/clustering/modularity.py) | Shared clustering scores and search functions |
| [`partition_visualization.py`](portland/clustering/partition_visualization.py) | Plotting helpers for candidate partitions |
| [`plot_m_statistic_histograms.py`](cross_dataset/plot_m_statistic_histograms.py) | BT and Scottish histogram functions; direct execution renders BT at B-bloc proportion 0.7 |

The Portland runner executes clustering only with `--diagnostics`. These searches can be expensive.

## Running an individual plotter

From the repository root:

```sh
uv run --locked python pipelines/scottish/plots/plot_um_iia_scatter.py
uv run --locked python pipelines/portland/plots/plot_boost_matrix.py --district all
QF_BT_STATS_DIR=stats/bt_2_bloc_profile_stats_final_experiment \
  uv run --locked python pipelines/bradley_terry/plots/plot_um_iia_scatter.py
```

Standalone scripts read preserved statistics by default and write under `results/generated/`.
Use `QF_STATS_DIR`, `QF_BT_STATS_DIR`, and `QF_BOOTSTRAP_DIR` to select inputs and `QF_RESULTS_DIR`
to choose a separate output tree. Script moves do not change the figure filenames or result
directory layouts. Importing pipeline modules does not run their analyses; execute a script or
call its `main()` function explicitly. Some plotters do not implement `--help`; consult their
module docstring and this index before launching a batch.

The BT runner was renamed from `run_2_bloc_BT_pipeline.sh` to `run_bt_pipeline.sh`. The primary
BT collector is now `bradley_terry/collect_metrics.py`, replacing the `final_set_v2` filename.
Dataset directories use lowercase names; old `NY/` paths now live under `new_york/`.
