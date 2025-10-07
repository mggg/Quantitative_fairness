from pathlib import Path
from glob import glob
import json
from itertools import product
import numpy as np
import matplotlib.pyplot as plt

# Imports from this folder
from colors import colors2 as colors
from metric_lists import (
    iia_metric_list,
    um_metric_list,
    variant_list,
)


script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()
plots_dir = top_dir / "plots" / "bt_plots" / "cohesion_sweep_plots"

cohesion_combinations = [
    (0.7, 0.7),
    (0.7, 0.9),
    (0.9, 0.7),
    (0.9, 0.9),
]

bprop = "*"
voting_rule = "*"
for (
    metric,
    variant,
) in product(iia_metric_list, variant_list):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = (
        plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_cohesion.png"
    )

    cohesion_combo_to_data = {
        cohesion_combo: np.array([-1.0, -1.0])
        for cohesion_combo in cohesion_combinations
    }

    for cohesion_combo in cohesion_combinations:
        cohesion_strs = [f"{a:.2f}" for a in cohesion_combo]
        cohesion_str = f"({','.join(cohesion_strs)})"
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_None"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_{cohesion_str}"
            f"__TYPE_*"
            f"__TIEBREAK_*"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = [list()] * len(all_files)
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        cohesion_combo_to_data[cohesion_combo] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(cohesion_combo_to_data.items()):
        data_points = np.array(data_points).reshape(-1, 2)
        ax.scatter(
            # data_points[:, 0] - 0.1 * idx, # used for debugging colors
            data_points[:, 0],
            data_points[:, 1],
            label=rule,
            color=colors[idx],
            edgecolors="none",
            alpha=0.7,
        )

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


for (
    metric,
    variant,
) in product(um_metric_list, variant_list):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = (
        plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_cohesion.png"
    )

    cohesion_combo_to_data = {
        cohesion_combo: np.array([-1.0, -1.0])
        for cohesion_combo in cohesion_combinations
    }

    for cohesion_combo in cohesion_combinations:
        cohesion_strs = [f"{a:.2f}" for a in cohesion_combo]
        cohesion_str = f"({','.join(cohesion_strs)})"
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_asin"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_{cohesion_str}"
            f"__TYPE_*"
            f"__TIEBREAK_*"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = [list()] * len(all_files)
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        cohesion_combo_to_data[cohesion_combo] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(cohesion_combo_to_data.items()):
        data_points = np.array(data_points).reshape(-1, 2)
        ax.scatter(
            # data_points[:, 0] - 0.1 * idx, # used for debugging colors
            data_points[:, 0],
            data_points[:, 1],
            label=rule,
            color=colors[idx],
            edgecolors="none",
            alpha=0.7,
        )

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
