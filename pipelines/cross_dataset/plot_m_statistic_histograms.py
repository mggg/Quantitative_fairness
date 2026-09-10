"""Create M-statistic histograms for Scottish and Bradley-Terry outputs."""

import json
import math
import sys
from glob import glob
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry.plots._data import load_metric_samples

from voting_metrics_main_code.constants import (
    BT_BLOC_PROPORTIONS,
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR, STATS_INPUT

scottish_plots_dir = PLOTS_DIR / "scottish" / "M_histograms"
bt_plots_dir = PLOTS_DIR / "bt_plots" / "M_histograms"


def inverse_interp(x: float) -> float:
    """Invert the ASIN interpolation back to M-space.

    Args:
        x (float): Interpolated value in [0, 1].

    Returns:
        float: The corresponding M value.
    """
    return math.sin((math.pi / 2) * x) ** 2 / 2


def save_histogram(
    values: Sequence[float] | np.ndarray,
    rule: str,
    output_file: Path,
    bin_width: float,
    upper_limit: float,
) -> None:
    """Save a probability histogram with the shared M-statistic plot styling.

    Args:
        values (Sequence[float] | np.ndarray): Observations to bin.
        rule (str): Voting rule used to select the plot color.
        output_file (Path): Destination image path.
        bin_width (float): Width of each histogram bin.
        upper_limit (float): Upper x-axis limit; the lower limit is zero.
    """
    _, axes = plt.subplots(figsize=(10, 6))
    sns.histplot(
        values,
        stat="probability",
        ax=axes,
        color=rule_color_map[rule],
        edgecolor=None,
        binwidth=bin_width,
        alpha=1,
    )

    axes.set_ylabel("")
    axes.set_xlim(0, upper_limit)
    axes.set_yticks([])
    axes.tick_params(axis="x", labelsize=16)

    plt.savefig(output_file, bbox_inches="tight", dpi=300)
    plt.close()


def make_scottish_M_histogram(rule: str) -> None:
    """Generate and save an M histogram for the Scottish datasets.

    Args:
        rule (str): Voting rule name used to locate the stats file.
    """
    file = glob(
        f"{STATS_INPUT}/scottish_stats/sigma_UM_worst_case_asin/**/*{rule}*lex_output.json",
        recursive=True,
    )[0]

    output_file = scottish_plots_dir / f"M_{rule}_scottish_histogram.png"
    scottish_plots_dir.mkdir(parents=True, exist_ok=True)

    with open(file, "r") as f:
        data = json.load(f)

    m_values = []
    total_count = 0

    for n_cands, val_dict in data.items():
        for file, rho_um in val_dict.items():
            total_count += 1

            if rho_um < 1.0:
                m_values.append(inverse_interp(rho_um))

    print(f"Rule: {rule}, Number of instances of M < 1/2: {len(m_values)} / {total_count}")
    save_histogram(m_values, rule, output_file, bin_width=0.005, upper_limit=0.5)


def make_bt_M_histograms(rule: str, bprop_values: Sequence[float] | None = None) -> None:
    """Generate M, ASIN, and odds histograms for BT simulations.

    Args:
        rule (str): Voting rule name used to locate the stats files.
        bprop_values (Sequence[float] | None, optional): B-bloc proportions to plot; None uses
            BT_BLOC_PROPORTIONS. Defaults to None.
    """
    if rule == "random":
        return

    bt_plots_dir.mkdir(parents=True, exist_ok=True)

    if bprop_values is None:
        bprop_values = BT_BLOC_PROPORTIONS

    for bprop in bprop_values:
        paths = glob(
            f"{BT_STATS_INPUT}/3_seats/sigma_UM/**/{rule}/"
            f"METRIC_sigma_UM__VARIANT_worst_case__INTERP_asin__*BPROP_{bprop}*TIEBREAK_lex.json"
        )
        scores = load_metric_samples(paths)
        asin_scores = [score for score in scores if score < 1.0]
        m_values = [inverse_interp(score) for score in asin_scores]
        odds_scores = np.array(m_values) / (1 - np.array(m_values))

        print(
            f"BPROP: {bprop}, Rule: {rule}, Number of instances of M < 1/2: {len(m_values)} /"
            f" {len(scores)}"
        )

        for label, values, bin_width, upper_limit in (
            ("M", m_values, 0.005, 0.5),
            ("ASIN", asin_scores, 0.01, 1.0),
            ("ODDS", odds_scores, 0.01, 1.0),
        ):
            output_file = bt_plots_dir / f"{label}_{rule}__BPROP_{bprop}_bt_histogram.png"
            save_histogram(values, rule, output_file, bin_width, upper_limit)


def make_legend() -> None:
    """Render a legend for the rule color map."""
    _, ax = plt.subplots(figsize=(6, 4))

    for rule, color in rule_color_map.items():
        ax.plot([], [], color=color, label=rule, linewidth=10)

    ax.legend()
    # plt.savefig(
    #     bt_plots_dir / "legend.png",
    #     bbox_inches="tight",
    #     dpi=300,
    # )
    plt.show()
    plt.close()


def main() -> None:
    """Save BT M, ASIN, and odds histograms for B-bloc proportion 0.7 under each nonrandom rule."""
    for rule in rule_color_map:
        # make_scottish_M_histogram(rule)
        make_bt_M_histograms(rule, [0.7])


if __name__ == "__main__":
    main()
    # make_legend()
