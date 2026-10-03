"""Plot mean vs std colored by cohesion parameters for BT metrics."""

import argparse
import sys
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from archive.pipelines.bradley_terry.plots._data import find_metric_files, load_metric_summaries
from archive.pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    um_metric_list,
    variant_list,
)
from archive.pipelines.bradley_terry.plots._palettes import colors2 as colors
from voting_metrics_main_code.constants import BT_COHESION_COMBINATIONS as cohesion_combinations
from voting_metrics_main_code.replication import ROOT


def load_metric_groups(
    metric: str,
    variant: str,
    interpolation_type: str,
    tiebreak: str,
    *,
    bt_stats_root: Path,
    n_seats: int = 3,
) -> dict[tuple[float, float], np.ndarray]:
    """Load mean and standard-deviation points grouped by bloc cohesion.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        metric (str): Metric identifier in input filenames.
        variant (str): Metric aggregation variant.
        interpolation_type (str): Interpolation token; the string 'None' selects IIA data.
        tiebreak (str): Tiebreak token in input filenames.

    Returns:
        dict[tuple[float, float], np.ndarray]: Two-column summary arrays in configured group order.
    """
    groups = {}

    for cohesion_combo in cohesion_combinations:
        all_files = find_metric_files(
            bt_stats_root,
            metric,
            variant,
            interpolation_type,
            n_seats=n_seats,
            tiebreak=tiebreak,
            cohesion=cohesion_combo,
        )

        data_points = load_metric_summaries(all_files)

        groups[cohesion_combo] = np.array(data_points)

    return groups


def plot_metric(
    metric: str,
    variant: str,
    interpolation_type: str,
    tiebreak: str = "lex",
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save means versus standard deviations colored by bloc cohesion.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier in input filenames and the plot title.
        variant (str): Metric aggregation variant.
        interpolation_type (str): Interpolation token; the string 'None' selects IIA data.
        tiebreak (str, optional): Tiebreak token in input filenames. Defaults to 'lex'.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "cohesion_sweep_plots"

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_cohesion.png"

    groups = load_metric_groups(
        metric, variant, interpolation_type, tiebreak, bt_stats_root=bt_stats_root, n_seats=n_seats
    )

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (group, data_points) in enumerate(groups.items()):
        data_points = np.array(data_points).reshape(-1, 2)
        ax.scatter(
            data_points[:, 0],
            data_points[:, 1],
            label=group,
            color=colors[idx],
            edgecolors="none",
            alpha=0.7,
        )

    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean", fontsize=16)
    ax.set_ylabel("Standard Deviation", fontsize=16)
    ax.set_title(f"{metric} - {variant} with varying bloc cohesion", fontsize=16)
    ax.legend(title="Cohesion by Bloc")

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def main(
    *, bt_stats_root: Path | None = None, output_root: Path = ROOT / "code/archive", n_seats: int = 3
) -> None:
    """Save the configured BT metric comparisons grouped by bloc cohesion.

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

    for metric, variant in product(iia_metric_list, variant_list):
        plot_metric(
            metric,
            variant,
            "None",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )

    for metric, variant in product(um_metric_list, variant_list):
        plot_metric(
            metric,
            variant,
            "asin",
            bt_stats_root=bt_stats_root,
            output_root=output_root,
            n_seats=n_seats,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "code/archive")
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
