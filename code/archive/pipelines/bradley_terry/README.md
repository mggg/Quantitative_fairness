# Archived Bradley–Terry figures

These scripts use saved repository statistics to render the supplementary figures under
`code/archive/plots/bt_plots/`. They import the archived plotting helpers explicitly and share
`code/voting_metrics_main_code/constants.py` and `replication.py` with the main repository.

| Archived figure folder      | Plotting script          | Images currently retained |
| --------------------------- | ------------------------------------ | ------------------------: |
| `alpha_boxplots/`           | `plot_alpha_boxplots.py`             |                        16 |
| `alpha_sweep_plots/`        | `plot_alpha_sweep.py`                |                         8 |
| `b_bloc_sweep_boxplots/`    | `plot_bloc_proportion_boxplots.py`   |                        21 |
| `b_bloc_sweep_plots/`       | `plot_bloc_proportion_sweep.py`      |                         6 |
| `candidate_sweep_boxplots/` | `plot_candidate_count_boxplots.py`   |                        25 |
| `candidate_sweep_plots/`    | `plot_candidate_count_sweep.py`      |                         8 |
| `cohesion_sweep_plots/`     | `plot_cohesion_sweep.py`             |                         8 |
| `iia_plots/`                | `plot_iia_by_rule.py`                |                         4 |
| `mean_vs_std/`              | `plot_mean_vs_standard_deviation.py` |                        32 |
| `mean_vs_var/`              | [`plot_um_mean_vs_variance.py`](../../../pipelines/bradley_terry/plots/plot_um_mean_vs_variance.py)        |                         6 |
| `um_plots/`                 | `plot_um_by_rule.py`                 |                         4 |

The mean-versus-variance figure uses the linked maintained plotter; pass
`--output-dir code/archive` to write its figures into this archive.

Run an archived plotter from the repository root, for example:

```sh
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_sweep.py
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant average
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py --variant worst_case
```

Plotters default to three seats, read `stats/bt_2_bloc_profile_stats/`, and write under
`code/archive/plots/`. The alpha boxplots instead read `stats/bt_alpha_grouped/`. Use `--bt-stats-dir`
(or the alpha boxplots' `--stats-dir` parent directory) to select different inputs. `--output-dir`
selects a run root containing `plots/`; changing it does not change the input statistics.
Figures overwrite by default. These are the individual archive commands, not the primary recipes
copied into `code/archive/scripts/`.

`pool_alpha_metrics.py` is retained to rebuild alpha-grouped inputs from the saved BT scores.
It defaults to repository statistics for both input and output and skips existing pooled files.
To keep newly pooled inputs in the archive instead:

```sh
uv run --locked python code/archive/pipelines/bradley_terry/pool_alpha_metrics.py --output-dir code/archive
uv run --locked python code/archive/pipelines/bradley_terry/plots/plot_alpha_boxplots.py \
  --stats-dir code/archive/stats --variant average
```

The archived copy omits profile generation, election/metric collection, and proportionality
computation. Those stages are not needed to plot the saved scores. The waterfall and UM–IIA
scatter scripts are also omitted because their output folders are absent from this plot archive.
The three modules in `plots/` whose names start with `_` supply loading, metric selections, and
palettes to the retained plotters.

## Figure sources in notebooks

Three figure families have source code in `code/archive/notebooks/`, outside this copied pipeline:

| Archived figure folder | Source notebook                                                                           | Images |
| ---------------------- | ----------------------------------------------------------------------------------------- | -----: |
| `disprop_histograms/`  | [`collect_bt_proporitonality.ipynb`](../../notebooks/collect_bt_proporitonality.ipynb) |      7 |
| `prop_v_iia_plots/`    | [`prop_v_iia_plots.ipynb`](../../notebooks/prop_v_iia_plots.ipynb)                     |      6 |
| `prop_v_um_plots/`     | [`prop_v_iia_plots.ipynb`](../../notebooks/prop_v_iia_plots.ipynb)                     |      6 |

The histogram code uses observed minus expected representation from `stats/bt_proportionality/`.
The scatter notebook joins that quantity to per-profile IIA or UM scores from
`stats/bt_2_bloc_profile_stats/`. All three export commands are currently commented out; the
notebooks' relative paths assume execution from their containing directory. These sources have not
been converted to standalone archive plotters. The waterfall plotter produces a different figure
family and is not needed by these notebooks.
