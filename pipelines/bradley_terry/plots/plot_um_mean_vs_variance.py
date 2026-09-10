"""Plot UM means against variances for each interpolation type."""

import sys
from glob import glob
from pathlib import Path
from pprint import pprint as print

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import load_metric_summaries

from pipelines.bradley_terry.plots._metrics import (
    interpolation_type_list,
    um_metric_list,
)

from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR

colors = ["#FB607F", "#A76BCF", "#FB8B24"]


plots_dir = PLOTS_DIR / "bt_plots" / "mean_vs_var"

metric_to_plot_name = {
    "sigma_UM": "rho_UM",
    "sigma_UM_winner_set": "sigma_UM",
}

# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================


def main() -> None:
    """Save BT UM means versus population variances for each metric and interpolation."""
    for metric in um_metric_list:
        plots_dir.mkdir(parents=True, exist_ok=True)

        for idx, interpolation_type in enumerate(interpolation_type_list):
            output_file = plots_dir / (
                f"{interpolation_type}__{metric_to_plot_name[metric]}__worst_case__mean_vs_var.png"
            )
            file_basename = (
                f"METRIC_{metric}"
                f"__VARIANT_worst_case"
                f"__INTERP_{interpolation_type}"
                f"__NCANDS_(*)"
                f"__SEATS_3"
                f"__BPROP_*"
                f"__ALPHA_(*)"
                f"__COHESION_(*)"
                f"__TYPE_*"
                f"__TIEBREAK_lex"
            )

            all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

            if len(all_files) == 0:
                print(file_basename)

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
    main()
