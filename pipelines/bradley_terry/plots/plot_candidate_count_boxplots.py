"""Build boxplots across candidate-count sweeps for BT metrics."""

import sys
from glob import glob
from itertools import product
from pathlib import Path
from typing import Mapping, Sequence, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.legend import Legend

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import load_metric_samples

from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    um_metric_list,
)

from voting_metrics_main_code.constants import (
    BT_CANDIDATE_COMBINATIONS as candidate_count_combinations,
    COMPARISON_RULE_LABELS as new_names,
    COMPARISON_RULE_ORDER as voting_rule_list,
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR


plots_dir = PLOTS_DIR / "bt_plots" / "candidate_sweep_boxplots"


def save_legend_only(
    legend: Legend,
    filename: str | Path,
    pad: float = 1.1,
    dpi: int = 300,
    transparent: bool = False,
) -> None:
    """Save a legend as a standalone image.

    Args:
        legend (Legend): Matplotlib legend to export.
        filename (str | Path): Path to write the legend image.
        pad (float, optional): Padding factor for legend bounds. Defaults to 1.1.
        dpi (int, optional): Output DPI. Defaults to 300.
        transparent (bool, optional): Whether to use a transparent background. Defaults to False.
    """
    fig = cast(Figure, legend.axes.figure)  # the parent figure
    fig.canvas.draw()  # need a renderer before measuring bbox

    # legend bbox in display coords → inches
    bbox = legend.get_window_extent().expanded(pad, pad)
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, transparent=transparent)


def build_plot_for_metric(
    rule_to_data_dict: Mapping[str, Sequence[float] | np.ndarray],
    ax: Axes,
    rule_color_map: Mapping[str, str] | None = None,
    legend: bool = False,
) -> Axes:
    """Create a single boxplot panel for a metric.

    Args:
        rule_to_data_dict (Mapping[str, Sequence[float] | np.ndarray]): Mapping of rule name to
            score arrays.
        ax (Axes): Matplotlib axes to draw into.
        rule_color_map (Mapping[str, str] | None, optional): Optional mapping of rule to color.
            Defaults to None.
        legend (bool, optional): Whether to render the legend on the axes. Defaults to False.

    Returns:
        Axes: The axes with the plot.
    """
    df = pd.DataFrame.from_dict(dict(rule_to_data_dict))
    long = df.melt(var_name="rule", value_name="score")
    long["group"] = ""  # single x category

    sns.boxplot(
        data=long,
        x="group",
        y="score",
        hue="rule",
        ax=ax,
        palette=rule_color_map,
        whis=[1, 99],  # type: ignore[arg-type]
        dodge=True,
        legend=legend,
    )
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])  # hide x-axis ticks
    ax.set_xticklabels([])  # hide x-axis labels

    if legend:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")

    return ax


def load_rule_samples(
    metric: str, c1: int, c2: int, variant: str, interpolation_type: str, tiebreak: str = "lex"
) -> dict[str, np.ndarray]:
    """Load pooled metric samples by voting rule for fixed candidate counts.

    Args:
        metric (str): Metric identifier used in the statistics filenames.
        c1 (int): Number of candidates in bloc A.
        c2 (int): Number of candidates in bloc B.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
        tiebreak (str, optional): Tiebreak rule token used in the statistics filenames. Defaults to
            'lex'.

    Returns:
        dict[str, np.ndarray]: Score arrays keyed by rule in the configured rule order. Each array
            retains the matched file and observation order.
    """
    voting_rule_to_data = {}

    for voting_rule in voting_rule_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_({c1:02d}_{c2:02d})"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

        data_points = load_metric_samples(all_files)

        voting_rule_to_data[voting_rule] = np.array(data_points)

    return voting_rule_to_data


def plot_metric_boxplot(
    metric: str, c1: int, c2: int, variant: str, interpolation_type: str
) -> None:
    """Save one voting-rule boxplot comparison for fixed candidate counts.

    Args:
        metric (str): Metric identifier used in the statistics filenames.
        c1 (int): Number of candidates in bloc A.
        c2 (int): Number of candidates in bloc B.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}_candidates_{(c1, c2)}_boxplot.png"

    voting_rule_to_data = load_rule_samples(metric, c1, c2, variant, interpolation_type)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    build_plot_for_metric(
        voting_rule_to_data,
        ax=ax,
        rule_color_map=rule_color_map,
    )

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def plot_rule_legend() -> None:
    """Save the standalone voting-rule legend beside the boxplots."""
    metric = um_metric_list[0]
    c1, c2 = candidate_count_combinations[0]
    plots_dir.mkdir(parents=True, exist_ok=True)

    voting_rule_to_data = load_rule_samples(metric, c1, c2, "worst_case", "asin")

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    ax = build_plot_for_metric(voting_rule_to_data, ax=ax, rule_color_map=rule_color_map)
    legend = ax.get_legend()

    handles, labels = ax.get_legend_handles_labels()
    labels = [new_names[label] for label in labels]
    legend = ax.legend(handles, labels, title="Voting rule", loc=(1.02, 0.5))

    output_plot_name = f"{plots_dir}/boxplot_legend.png"
    save_legend_only(legend, output_plot_name, pad=1.1, dpi=300, transparent=False)

    plt.close()


def main() -> None:
    """Save the BT boxplot comparisons by candidate counts and their shared legend."""
    for metric, (c1, c2) in product(iia_metric_list, candidate_count_combinations):
        plot_metric_boxplot(metric, c1, c2, "average", "None")

    for metric, (c1, c2) in product(um_metric_list, candidate_count_combinations):
        plot_metric_boxplot(metric, c1, c2, "worst_case", "asin")

    plot_rule_legend()


if __name__ == "__main__":
    main()
