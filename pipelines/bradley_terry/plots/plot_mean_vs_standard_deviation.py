"""Generate mean vs std plots for BT metrics and interpolation types."""

import argparse
import sys
from itertools import product
from pathlib import Path
from pprint import pprint as print

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import find_metric_files, load_metric_summaries
from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    interpolation_type_list,
    um_metric_list,
    variant_list,
)
from pipelines.bradley_terry.plots._palettes import colors2 as colors
from voting_metrics_main_code.replication import ROOT

# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================


def plot_um_summary(
    metric: str,
    variant: str,
    voting_rule: str,
    output_file: Path,
    title: str,
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save UM means versus standard deviations for a voting-rule selection.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier used in the statistics filenames.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        voting_rule (str): Rule token or '*' to match all rules in the input filenames.
        output_file (Path): Destination file path.
        title (str): Figure title.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "mean_vs_std"

    tiebreak = "lex"

    plots_dir.mkdir(parents=True, exist_ok=True)

    interpolation_to_points = {
        interpolation_type: np.array([-1.0, -1.0]) for interpolation_type in interpolation_type_list
    }

    for interpolation_type in interpolation_type_list:
        all_files = find_metric_files(
            bt_stats_root,
            metric,
            variant,
            interpolation_type,
            n_seats=n_seats,
            rule=voting_rule,
            tiebreak=tiebreak,
        )

        data_points = load_metric_summaries(all_files)

        interpolation_to_points[interpolation_type] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (interpolation_type, data_points) in enumerate(interpolation_to_points.items()):
        data_points = np.array(data_points)
        ax.scatter(
            data_points[:, 0],
            data_points[:, 1],
            label=interpolation_type,
            color=colors[idx],
            edgecolors="none",
            alpha=0.7,
        )

    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean")
    ax.set_ylabel("Standard Deviation")
    ax.set_title(title)
    ax.legend()

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def plot_iia_summary(
    metric: str,
    variant: str,
    voting_rule: str,
    output_file: Path,
    title: str,
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save IIA means versus standard deviations for a voting-rule selection.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier used in the statistics filenames.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        voting_rule (str): Rule token or '*' to match all rules in the input filenames.
        output_file (Path): Destination file path.
        title (str): Figure title.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "mean_vs_std"

    tiebreak = "lex"

    plots_dir.mkdir(parents=True, exist_ok=True)

    all_files = find_metric_files(
        bt_stats_root, metric, variant, "None", n_seats=n_seats, rule=voting_rule, tiebreak=tiebreak
    )

    data_points = load_metric_summaries(all_files)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    data_points = np.array(data_points)
    ax.scatter(
        data_points[:, 0],
        data_points[:, 1],
        label=interpolation_type_list[-1],
        color=colors[0],
        edgecolors="none",
        alpha=0.7,
    )
    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean")
    ax.set_ylabel("Standard Deviation")
    ax.set_title(title)

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def main(*, bt_stats_root: Path | None = None, output_root: Path = ROOT, n_seats: int = 3) -> None:
    """Save BT mean-versus-standard-deviation figures for configured metrics and rules.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or output_root / "stats/bt_2_bloc_profile_stats").resolve()
    print(f"BT statistics: {bt_stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    plots_dir = output_root / "plots" / "bt_plots" / "mean_vs_std"

    voting_rules = ("borda", "plurality", "stv")

    for metric, variant in product(um_metric_list, variant_list):
        plot_um_summary(
            metric,
            variant,
            "*",
            plots_dir / f"{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant}",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    for metric, variant, rule in product(um_metric_list, variant_list, voting_rules):
        plot_um_summary(
            metric,
            variant,
            rule,
            plots_dir / f"{rule}__{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant} - {rule}",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    # Unprefixed IIA figures retain the final rule from the UM comparison sequence.
    for metric, variant in product(iia_metric_list, variant_list):
        plot_iia_summary(
            metric,
            variant,
            voting_rules[-1],
            plots_dir / f"{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant}",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    for metric, variant, rule in product(iia_metric_list, variant_list, voting_rules):
        plot_iia_summary(
            metric,
            variant,
            rule,
            plots_dir / f"{rule}__{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant} - {rule}",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
