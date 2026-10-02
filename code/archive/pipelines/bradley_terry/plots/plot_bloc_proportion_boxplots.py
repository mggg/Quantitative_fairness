"""Build boxplots across B-bloc proportions for BT metrics."""

import argparse
import sys
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

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from archive.pipelines.bradley_terry.plots._data import find_metric_files, load_metric_samples
from archive.pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    um_metric_list,
)
from voting_metrics_main_code.constants import (
    BT_BLOC_PROPORTIONS as b_bloc_proportions,
)
from voting_metrics_main_code.constants import (
    COMPARISON_RULE_LABELS as new_names,
)
from voting_metrics_main_code.constants import (
    COMPARISON_RULE_ORDER as voting_rule_list,
)
from voting_metrics_main_code.constants import (
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import ROOT


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
    metric: str,
    b_prop: float,
    variant: str,
    interpolation_type: str,
    tiebreak: str = "lex",
    *,
    bt_stats_root: Path,
    n_seats: int = 3,
) -> dict[str, np.ndarray]:
    """Load pooled metric samples by voting rule for fixed bloc proportion.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        metric (str): Metric identifier used in the statistics filenames.
        b_prop (float): Proportion of voters in bloc B.
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
        all_files = find_metric_files(
            bt_stats_root,
            metric,
            variant,
            interpolation_type,
            n_seats=n_seats,
            rule=voting_rule,
            tiebreak=tiebreak,
            bloc_proportion=b_prop,
        )

        data_points = load_metric_samples(all_files)

        voting_rule_to_data[voting_rule] = np.array(data_points)

    return voting_rule_to_data


def plot_metric_boxplot(
    metric: str,
    b_prop: float,
    variant: str,
    interpolation_type: str,
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save one voting-rule boxplot comparison for fixed bloc proportion.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier used in the statistics filenames.
        b_prop (float): Proportion of voters in bloc B.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "b_bloc_sweep_boxplots"

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}_b-bloc_prop_{b_prop}_boxplot.png"

    voting_rule_to_data = load_rule_samples(
        metric, b_prop, variant, interpolation_type, bt_stats_root=bt_stats_root, n_seats=n_seats
    )

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


def plot_rule_legend(*, bt_stats_root: Path, output_root: Path, n_seats: int = 3) -> None:
    """Save the standalone voting-rule legend beside the boxplots.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "b_bloc_sweep_boxplots"

    metric = um_metric_list[0]
    b_prop = b_bloc_proportions[0]
    plots_dir.mkdir(parents=True, exist_ok=True)

    voting_rule_to_data = load_rule_samples(
        metric, b_prop, "worst_case", "asin", bt_stats_root=bt_stats_root, n_seats=n_seats
    )

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    ax = build_plot_for_metric(
        voting_rule_to_data,
        ax=ax,
        rule_color_map=rule_color_map,
    )
    legend = ax.get_legend()

    handles, labels = ax.get_legend_handles_labels()
    labels = [new_names[label] for label in labels]
    legend = ax.legend(handles, labels, title="Voting rule", loc=(1.02, 0.5))

    output_plot_name = f"{plots_dir}/boxplot_legend.png"
    save_legend_only(legend, output_plot_name, pad=1.1, dpi=300, transparent=False)

    plt.close()


def main(
    *, bt_stats_root: Path | None = None, output_root: Path = ROOT / "code/archive", n_seats: int = 3
) -> None:
    """Save the BT boxplot comparisons by bloc proportion and their shared legend.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            repository statistics tree.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT / "code/archive".
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or ROOT / "stats/bt_2_bloc_profile_stats").resolve()
    print(f"BT statistics: {bt_stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    for metric, b_prop in product(iia_metric_list, b_bloc_proportions):
        plot_metric_boxplot(
            metric,
            b_prop,
            "average",
            "None",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    for metric, b_prop in product(um_metric_list, b_bloc_proportions):
        plot_metric_boxplot(
            metric,
            b_prop,
            "worst_case",
            "asin",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    plot_rule_legend(bt_stats_root=bt_stats_root, output_root=output_root, n_seats=n_seats)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "code/archive")
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
