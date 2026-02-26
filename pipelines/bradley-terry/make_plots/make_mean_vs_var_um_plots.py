"""Generate mean vs std plots for BT metrics and interpolation types."""

from pathlib import Path
from glob import glob
from pprint import pprint as print
from itertools import product
import json
import numpy as np

import matplotlib.pyplot as plt
from metric_lists import (
    um_metric_list,
    interpolation_type_list,
)

colors = ["#FB607F", "#A76BCF", "#FB8B24"]

script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()

plots_dir = top_dir / "plots" / "bt_plots" / "mean_vs_var"

metric_to_plot_name = {
    "sigma_UM": "rho_UM",
    "sigma_UM_winner_set": "sigma_UM",
}

# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================

for metric in um_metric_list:
    plots_dir.mkdir(parents=True, exist_ok=True)

    inerpolation_type_to_data = {
        interpolation_type: np.array([-1.0, -1.0])
        for interpolation_type in interpolation_type_list
    }

    for idx, interpolation_type in enumerate(interpolation_type_list):
        output_file = (
            plots_dir
            / f"{interpolation_type}__{metric_to_plot_name[metric]}__worst_case__mean_vs_var.png"
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

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        if len(all_files) == 0:
            print(file_basename)

        data_points = [list()] * len(all_files)
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points[i] = [float(np.mean(data)), float(np.var(data))]

        inerpolation_type_to_data[interpolation_type] = np.array(data_points)

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
            # x_line = np.linspace(data_points[:, 0].min(), data_points[:, 0].max(), 100)
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
