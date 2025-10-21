from pathlib import Path
from glob import glob
from pprint import pprint as print
from itertools import product
import json
import numpy as np

import matplotlib.pyplot as plt
from colors import colors2 as colors
from metric_lists import (
    um_metric_list,
    iia_metric_list,
    variant_list,
    interpolation_type_list,
)


script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()

plots_dir = top_dir / "plots" / "bt_plots" / "mean_vs_std"


bprop = "*"
voting_rule = "*"
tiebreak = "lex"

# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================

for (
    metric,
    variant,
) in product(um_metric_list, variant_list):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std.png"

    inerpolation_type_to_data = {
        interpolation_type: np.array([-1.0, -1.0])
        for interpolation_type in interpolation_type_list
    }

    for interpolation_type in interpolation_type_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{bprop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
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

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        inerpolation_type_to_data[interpolation_type] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (interpolation_type, data_points) in enumerate(
        inerpolation_type_to_data.items()
    ):
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
    ax.set_title(f"{metric} - {variant}")
    ax.legend()
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


# ===========================
#   UM PLOTS BY VOTING RULE
# ===========================


voting_rule_list = [
    "borda",
    "plurality",
    "stv",
]
for (
    metric,
    variant,
    voting_rule,
) in product(
    um_metric_list,
    variant_list,
    voting_rule_list,
):

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{voting_rule}__{metric}__{variant}__mean_vs_std.png"

    inerpolation_type_to_data = {
        interpolation_type: np.array([-1.0, -1.0])
        for interpolation_type in interpolation_type_list
    }

    for interpolation_type in interpolation_type_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{bprop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
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

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        inerpolation_type_to_data[interpolation_type] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (interpolation_type, data_points) in enumerate(
        inerpolation_type_to_data.items()
    ):
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
    ax.set_title(f"{metric} - {variant} - {voting_rule}")
    ax.legend()
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


voting_rule_list = [
    "borda",
    "plurality",
    "stv",
]
for (
    metric,
    variant,
    voting_rule,
) in product(
    um_metric_list,
    variant_list,
    voting_rule_list,
):

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{voting_rule}__{metric}__{variant}__mean_vs_std.png"

    inerpolation_type_to_data = {
        interpolation_type: np.array([-1.0, -1.0])
        for interpolation_type in interpolation_type_list
    }

    for interpolation_type in interpolation_type_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{bprop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
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

            data_points[i] = [float(np.mean(data)), float(np.std(data))]

        inerpolation_type_to_data[interpolation_type] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (interpolation_type, data_points) in enumerate(
        inerpolation_type_to_data.items()
    ):
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
    ax.set_title(f"{metric} - {variant} - {voting_rule}")
    ax.legend()
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()

# =============================
#   IIA PLOTS BY OVERALL TYPE
# =============================

for (
    metric,
    variant,
) in product(iia_metric_list, variant_list):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std.png"

    file_basename = (
        f"METRIC_{metric}"
        f"__VARIANT_{variant}"
        f"__INTERP_None"
        f"__NCANDS_(*)"
        f"__SEATS_3"
        f"__BPROP_{bprop}"
        f"__ALPHA_(*)"
        f"__COHESION_(*)"
        f"__TYPE_{voting_rule}"
        f"__TIEBREAK_{tiebreak}"
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

        data_points[i] = [float(np.mean(data)), float(np.std(data))]

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    data_points = np.array(data_points)
    ax.scatter(
        data_points[:, 0],
        data_points[:, 1],
        label=interpolation_type,
        color=colors[0],
        edgecolors="none",
        alpha=0.7,
    )

    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean")
    ax.set_ylabel("Standard Deviation")
    ax.set_title(f"{metric} - {variant}")
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


# ============================
#   IIA PLOTS BY VOTING RULE
# ============================


voting_rule_list = [
    "borda",
    "plurality",
    "stv",
]
for (
    metric,
    variant,
    voting_rule,
) in product(
    iia_metric_list,
    variant_list,
    voting_rule_list,
):

    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{voting_rule}__{metric}__{variant}__mean_vs_std.png"

    file_basename = (
        f"METRIC_{metric}"
        f"__VARIANT_{variant}"
        f"__INTERP_None"
        f"__NCANDS_(*)"
        f"__SEATS_3"
        f"__BPROP_{bprop}"
        f"__ALPHA_(*)"
        f"__COHESION_(*)"
        f"__TYPE_{voting_rule}"
        f"__TIEBREAK_{tiebreak}"
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

        data_points[i] = [float(np.mean(data)), float(np.std(data))]

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    data_points = np.array(data_points)
    ax.scatter(
        data_points[:, 0],
        data_points[:, 1],
        label=interpolation_type,
        color=colors[0],
        edgecolors="none",
        alpha=0.7,
    )
    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Mean")
    ax.set_ylabel("Standard Deviation")
    ax.set_title(f"{metric} - {variant} - {voting_rule}")
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()
