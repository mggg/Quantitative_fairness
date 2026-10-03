"""Create M-statistic histograms for Scottish and Bradley-Terry outputs."""

import argparse
import json
import math
import sys
from glob import escape, glob
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry.plots._data import find_metric_files, load_metric_samples
from voting_metrics_main_code.constants import (
    BT_BLOC_PROPORTIONS,
)
from voting_metrics_main_code.constants import (
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import ROOT


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


def make_scottish_M_histogram(rule: str, *, stats_root: Path, output_root: Path) -> None:
    """Generate and save an M histogram for the Scottish datasets.

    Args:
        rule (str): Voting rule name used to locate the stats file.
        stats_root (Path): Parent of the dataset statistics directories.
        output_root (Path): Run root containing stats, plots, and tables.
    """
    scottish_plots_dir = output_root / "plots" / "scottish" / "M_histograms"

    file = glob(
        f"{escape(str(stats_root))}/scottish_stats/sigma_UM_worst_case_asin/**/*{rule}*lex_output.json",
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


def make_bt_M_histograms(
    rule: str,
    bprop_values: Sequence[float] | None = None,
    *,
    bt_stats_root: Path,
    n_seats: int = 3,
    output_root: Path,
) -> None:
    """Generate M, ASIN, and odds histograms for BT simulations.

    Args:
        rule (str): Voting rule name used to locate the stats files.
        bprop_values (Sequence[float] | None, optional): B-bloc proportions to plot; None uses
            BT_BLOC_PROPORTIONS. Defaults to None.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        n_seats (int, optional): Seat count of the selected experiment. Defaults to 3.
        output_root (Path): Run root containing stats, plots, and tables.
    """
    bt_plots_dir = output_root / "plots" / "bt_plots" / "M_histograms"

    if rule == "random":
        return

    bt_plots_dir.mkdir(parents=True, exist_ok=True)

    if bprop_values is None:
        bprop_values = BT_BLOC_PROPORTIONS

    for bprop in bprop_values:
        paths = find_metric_files(
            bt_stats_root,
            "sigma_UM",
            "worst_case",
            "asin",
            n_seats=n_seats,
            rule=rule,
            bloc_proportion=bprop,
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


def main(*, bt_stats_root: Path | None = None, output_root: Path = ROOT, n_seats: int = 3) -> None:
    """Save BT M, ASIN, and odds histograms for B-bloc proportion 0.7 under each nonrandom rule.

    Args:
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            selected run root. Defaults to None.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_seats (int, optional): Seat count of the selected experiment. Defaults to 3.
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or output_root / "stats/bt_2_bloc_profile_stats").resolve()

    for rule in rule_color_map:
        # make_scottish_M_histogram(rule)
        make_bt_M_histograms(
            rule, [0.7], bt_stats_root=bt_stats_root, output_root=output_root, n_seats=n_seats
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-seats", type=int, default=3, help="Seat count of the BT experiment.")
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)

    # make_legend()
