"""Plot mean vs std colored by candidate combinations for BT metrics."""

import sys
from glob import glob
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import load_metric_summaries

from pipelines.bradley_terry.plots._palettes import colors2 as colors
from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
    um_metric_list,
    variant_list,
)

from voting_metrics_main_code.constants import BT_CANDIDATE_COMBINATIONS as candidate_combinations
from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR

plots_dir = PLOTS_DIR / "bt_plots" / "candidate_sweep_plots"


def plot_iia_metric(metric: str, variant: str, tiebreak: str = "lex") -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_candidate.png"

    candidate_combo_to_data = {
        candidate_combo: np.array([-1.0, -1.0]) for candidate_combo in candidate_combinations
    }

    for candidate_combo in candidate_combinations:
        candidate_strs = [f"{a:02d}" for a in candidate_combo]
        candidate_str = f"({'_'.join(candidate_strs)})"
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_None"
            f"__NCANDS_{candidate_str}"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_*"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

        data_points = load_metric_summaries(all_files)

        candidate_combo_to_data[candidate_combo] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(candidate_combo_to_data.items()):
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
    ax.set_title(f"{metric} - {variant} with varying bloc candidate counts", fontsize=16)
    ax.legend(title="Candidate Counts by Bloc")
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def plot_um_metric(metric: str, variant: str, tiebreak: str = "lex") -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_candidate.png"

    candidate_combo_to_data = {
        candidate_combo: np.array([-1.0, -1.0]) for candidate_combo in candidate_combinations
    }

    for candidate_combo in candidate_combinations:
        candidate_strs = [f"{a:02d}" for a in candidate_combo]
        candidate_str = f"({'_'.join(candidate_strs)})"
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_asin"
            f"__NCANDS_{candidate_str}"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_*"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

        data_points = load_metric_summaries(all_files)

        candidate_combo_to_data[candidate_combo] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    for idx, (rule, data_points) in enumerate(candidate_combo_to_data.items()):
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
    ax.set_title(f"{metric} - {variant} with varying bloc candidate counts", fontsize=16)
    ax.legend(title="Candidate Counts by Bloc")
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def main() -> None:
    for metric, variant in product(iia_metric_list, variant_list):
        plot_iia_metric(metric, variant)
    for metric, variant in product(um_metric_list, variant_list):
        plot_um_metric(metric, variant)


if __name__ == "__main__":
    main()
