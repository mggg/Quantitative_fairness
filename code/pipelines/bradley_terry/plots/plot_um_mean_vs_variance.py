"""Plot UM means against variances for each interpolation type."""

import argparse
import sys
from pathlib import Path
from pprint import pprint as print

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import find_metric_files, load_metric_summaries
from pipelines.bradley_terry.plots._metrics import (
    interpolation_type_list,
    um_metric_list,
)
from voting_metrics_main_code.replication import ROOT

colors = ["#FB607F", "#A76BCF", "#FB8B24"]


metric_to_plot_name = {
    "sigma_UM": "rho_UM",
    "sigma_UM_winner_set": "sigma_UM",
}

# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================


def main(*, bt_stats_root: Path | None = None, output_root: Path = ROOT, n_seats: int = 3) -> None:
    """Save BT UM means versus population variances for each metric and interpolation.

    Args:
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            selected run root. Defaults to None.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or output_root / "stats/bt_2_bloc_profile_stats").resolve()
    print(f"BT statistics: {bt_stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    plots_dir = output_root / "plots" / "bt_plots" / "mean_vs_var"

    for metric in um_metric_list:
        plots_dir.mkdir(parents=True, exist_ok=True)

        for idx, interpolation_type in enumerate(interpolation_type_list):
            output_file = plots_dir / (
                f"{interpolation_type}__{metric_to_plot_name[metric]}__worst_case__mean_vs_var.png"
            )
            all_files = find_metric_files(
                bt_stats_root, metric, "worst_case", interpolation_type, n_seats=n_seats
            )

            data_points = load_metric_summaries(all_files, statistic="var")

            fig, ax = plt.subplots(figsize=(20, 20), dpi=300)
            print(f"NUMBER OF POINTS {len(data_points)}")
            data_points = np.array(data_points)
            ax.scatter(
                data_points[:, 0],
                data_points[:, 1],
                color=colors[idx],
                edgecolors="none",
                alpha=1.0,
            )

            # Add line of best fit
            if len(data_points) > 1:
                z = np.polyfit(data_points[:, 0], data_points[:, 1], 1)
                p = np.poly1d(z)
                xmin, xmax = -0.1, 1.1
                x_line = np.linspace(xmin, xmax, 100)
                ax.plot(x_line, p(x_line), color="black", linewidth=3, alpha=1.0)

            ax.set_xlim(-0.05, 1.05)
            ax.set_ylim(-0.005, 0.205)

            ax.set_yticks([0, 0.05, 0.1, 0.15, 0.2])
            ax.tick_params(axis="both", which="major", labelsize=24)

            plt.savefig(
                output_file,
                bbox_inches="tight",
                dpi=300,
            )
            plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
