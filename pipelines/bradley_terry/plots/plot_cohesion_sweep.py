"""Plot mean vs std colored by cohesion parameters for BT metrics."""

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

from voting_metrics_main_code.constants import BT_COHESION_COMBINATIONS as cohesion_combinations
from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR

plots_dir = PLOTS_DIR / "bt_plots" / "cohesion_sweep_plots"


def load_metric_groups(
    metric: str, variant: str, interpolation_type: str, tiebreak: str
) -> dict[tuple[float, float], np.ndarray]:
    """Load mean and standard-deviation points grouped by bloc cohesion.

    Args:
        metric (str): Metric identifier in input filenames.
        variant (str): Metric aggregation variant.
        interpolation_type (str): Interpolation token; the string 'None' selects IIA data.
        tiebreak (str): Tiebreak token in input filenames.

    Returns:
        dict[tuple[float, float], np.ndarray]: Two-column summary arrays in configured group order.
    """
    groups = {}

    for cohesion_combo in cohesion_combinations:
        cohesion_strs = [f"{a:.2f}" for a in cohesion_combo]
        cohesion_str = f"({','.join(cohesion_strs)})"
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_*"
            f"__ALPHA_(*)"
            f"__COHESION_{cohesion_str}"
            f"__TYPE_*"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{file_basename}.json")

        data_points = load_metric_summaries(all_files)

        groups[cohesion_combo] = np.array(data_points)

    return groups


def plot_metric(metric: str, variant: str, interpolation_type: str, tiebreak: str = "lex") -> None:
    """Save means versus standard deviations colored by bloc cohesion.

    Args:
        metric (str): Metric identifier in input filenames and the plot title.
        variant (str): Metric aggregation variant.
        interpolation_type (str): Interpolation token; the string 'None' selects IIA data.
        tiebreak (str, optional): Tiebreak token in input filenames. Defaults to 'lex'.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}__mean_vs_std_colored_by_cohesion.png"

    groups = load_metric_groups(metric, variant, interpolation_type, tiebreak)

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


def main() -> None:
    """Save the configured BT metric comparisons grouped by bloc cohesion."""
    for metric, variant in product(iia_metric_list, variant_list):
        plot_metric(metric, variant, "None")

    for metric, variant in product(um_metric_list, variant_list):
        plot_metric(metric, variant, "asin")


if __name__ == "__main__":
    main()
