"""Plot IIA metric summaries colored by election type."""

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
    variant_list,
)
from archive.pipelines.bradley_terry.plots._palettes import colors
from voting_metrics_main_code.replication import ROOT


def plot_iia_metric(
    metric: str,
    variant: str,
    tiebreak: str = "lex",
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save IIA means versus standard deviations colored by voting rule.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier used in the statistics filenames.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str, optional): Tiebreak rule token used in the statistics filenames. Defaults to
            'lex'.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "iia_plots"

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_election_type.png"

    voting_rule_to_data = {
        voting_rule: np.array([-1.0, -1.0]) for voting_rule in ["borda", "stv", "plurality"]
    }

    for voting_rule in ["borda", "stv", "plurality"]:
        all_files = find_metric_files(
            bt_stats_root,
            metric,
            variant,
            "None",
            n_seats=n_seats,
            rule=voting_rule,
            tiebreak=tiebreak,
        )

        data_points = load_metric_summaries(all_files)

        voting_rule_to_data[voting_rule] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(voting_rule_to_data.items()):
        data_points = np.array(data_points).reshape(-1, 2)
        ax.scatter(
            data_points[:, 0],
            data_points[:, 1],
            label=rule,
            color=colors[idx],
            edgecolors="none",
            alpha=0.7,
        )

    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean", fontsize=16)
    ax.set_ylabel("Standard Deviation", fontsize=16)
    ax.set_title(f"{metric} - {variant}", fontsize=16)
    ax.legend()

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def main(
    *, bt_stats_root: Path | None = None, output_root: Path = ROOT / "archive", n_seats: int = 3
) -> None:
    """Save the configured BT metric comparisons grouped by voting rule.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            repository statistics tree.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT / "archive".
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or ROOT / "stats/bt_2_bloc_profile_stats").resolve()
    print(f"BT statistics: {bt_stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    for metric, variant in product(iia_metric_list, variant_list):
        plot_iia_metric(
            metric, variant, bt_stats_root=bt_stats_root, output_root=output_root, n_seats=n_seats
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "archive")
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
