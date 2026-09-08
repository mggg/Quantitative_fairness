"""Generate mean vs std plots for BT metrics and interpolation types."""

import sys
from glob import glob
from itertools import product
from pathlib import Path
from pprint import pprint as print

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import load_metric_summaries

from pipelines.bradley_terry.plots._palettes import colors2 as colors
from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    interpolation_type_list,
    um_metric_list,
    variant_list,
)

from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR


plots_dir = PLOTS_DIR / "bt_plots" / "mean_vs_std"


# ============================
#   UM PLOTS BY OVERALL TYPE
# ============================


def plot_um_summary(
    metric: str, variant: str, voting_rule: str, output_file: Path, title: str
) -> None:
    bprop = "*"
    tiebreak = "lex"

    plots_dir.mkdir(parents=True, exist_ok=True)

    interpolation_to_points = {
        interpolation_type: np.array([-1.0, -1.0]) for interpolation_type in interpolation_type_list
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

        all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

        if len(all_files) == 0:
            print(file_basename)

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
    metric: str, variant: str, voting_rule: str, output_file: Path, title: str
) -> None:
    bprop = "*"
    tiebreak = "lex"

    plots_dir.mkdir(parents=True, exist_ok=True)

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

    all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

    if len(all_files) == 0:
        print(file_basename)

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


def main() -> None:
    voting_rules = ("borda", "plurality", "stv")
    for metric, variant in product(um_metric_list, variant_list):
        plot_um_summary(
            metric,
            variant,
            "*",
            plots_dir / f"{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant}",
        )

    for metric, variant, rule in product(um_metric_list, variant_list, voting_rules):
        plot_um_summary(
            metric,
            variant,
            rule,
            plots_dir / f"{rule}__{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant} - {rule}",
        )

    # Unprefixed IIA figures retain the final rule from the UM comparison sequence.
    for metric, variant in product(iia_metric_list, variant_list):
        plot_iia_summary(
            metric,
            variant,
            voting_rules[-1],
            plots_dir / f"{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant}",
        )

    for metric, variant, rule in product(iia_metric_list, variant_list, voting_rules):
        plot_iia_summary(
            metric,
            variant,
            rule,
            plots_dir / f"{rule}__{metric}__{variant}__mean_vs_std.png",
            f"{metric} - {variant} - {rule}",
        )


if __name__ == "__main__":
    main()
