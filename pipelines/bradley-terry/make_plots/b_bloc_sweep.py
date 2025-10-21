from pathlib import Path
from glob import glob
from itertools import product
import json
import numpy as np
import matplotlib.pyplot as plt
import sys

sys.path.append(
    "/mnt/efs/h/Dropbox/MADLAB/Git_Repos/replication/Quantitative_fairness/"
)

# Imports from this folder
from colors import colors3 as colors
from metric_lists import (
    iia_metric_list,
    um_metric_list,
    variant_list,
)


script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()
plots_dir = top_dir / "plots" / "bt_plots" / "b_bloc_sweep_plots"

b_bloc_proportions = [0.5, 0.6, 0.7, 0.8, 0.9]

bprop = "*"
voting_rule = "*"
variant = "average"
tiebreak = "lex"
for metric in iia_metric_list:
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = (
        plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_b-bloc_prop.png"
    )

    b_bloc_to_data = {b_prop: np.array([-1.0, -1.0]) for b_prop in b_bloc_proportions}

    for b_prop in b_bloc_proportions:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_None"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{b_prop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_*"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = [list()] * len(all_files)
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        b_bloc_to_data[b_prop] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(b_bloc_to_data.items()):
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
    ax.set_title(f"{metric} - {variant} by B-bloc Proportion", fontsize=16)
    ax.legend(title="B-bloc Proportion")
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
        plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_b-bloc_prop.png"
    )

    b_bloc_to_data = {b_prop: np.array([-1.0, -1.0]) for b_prop in b_bloc_proportions}

    for b_prop in b_bloc_proportions:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_asin"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{b_prop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_*"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = [list()] * len(all_files)

        low_value_frequency = []
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        b_bloc_to_data[b_prop] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(b_bloc_to_data.items()):
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
    ax.set_title(f"{metric} - {variant} by B-bloc Proportion", fontsize=16)
    ax.legend(title="B-bloc Proportion")
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()
