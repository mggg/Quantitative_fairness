"""Create M-statistic histograms for Scottish and Bradley-Terry outputs."""

import json
from glob import glob
import math
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()
scottish_plots_dir = top_dir / "plots" / "scottish" / "M_histograms"
bt_plots_dir = top_dir / "plots" / "bt_plots" / "M_histograms"

rule_color_map = {
    "borda": "#1460bc",  # lightblue
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}


def inverse_interp(x: float) -> float:
    """Invert the ASIN interpolation back to M-space.

    Args:
        x (float): Interpolated value in [0, 1].

    Returns:
        The corresponding M value.
    """
    return math.sin((math.pi / 2) * x) ** 2 / 2


def make_scottish_M_histogram(rule: str) -> None:
    """Generate and save an M histogram for the Scottish datasets.

    Args:
        rule (str): Voting rule name used to locate the stats file.
    """
    file = glob(
        f"{top_dir}/stats/scottish_stats/sigma_UM_worst_case_asin/**/*{rule}*lex_output.json",
        recursive=True,
    )[0]

    output_file = scottish_plots_dir / f"M_{rule}_scottish_histogram.png"
    with open(file, "r") as f:
        data = json.load(f)

    m_values = []
    total_count = 0
    for n_cands, val_dict in data.items():
        for file, rho_um in val_dict.items():
            total_count += 1
            if rho_um < 1.0:
                m_values.append(inverse_interp(rho_um))

    print(
        f"Rule: {rule}, Number of instances of M < 1/2: {len(m_values)} / {total_count}"
    )
    _, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(
        m_values,
        stat="probability",
        ax=ax,
        alpha=1,
        color=rule_color_map[rule],
        edgecolor=None,
        binwidth=0.005,
    )

    ax.set_ylabel("")
    ax.set_xlim(0, 0.5)
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=16)
    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()


def make_bt_M_histograms(rule: str, bprop_values: Sequence[float] | None = None) -> None:
    """Generate M, ASIN, and odds histograms for BT simulations.

    Args:
        rule (str): Voting rule name used to locate the stats files.
        bprop_values (Sequence[float] | None): Optional list of B-bloc proportions
            to plot.
    """
    if rule == "random":
        return

    if bprop_values is None:
        bprop_values = [0.5, 0.6, 0.7, 0.8, 0.9]
    for bprop in bprop_values:
        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/sigma_UM/**/{rule}/"
            f"METRIC_sigma_UM__VARIANT_worst_case__INTERP_asin__*BPROP_{bprop}*TIEBREAK_lex.json"
        )

        m_values = []
        asin_data = []
        total_count = 0
        for file in all_files:
            with open(file, "r") as f:
                data = json.load(f)

            for rho_um in data:
                total_count += 1
                if rho_um < 1.0:
                    asin_data.append(rho_um)
                    m_values.append(inverse_interp(rho_um))

        print(
            f"BPROP: {bprop}, Rule: {rule}, Number of instances of M < 1/2: {len(m_values)} / {total_count}"
        )
        output_file = bt_plots_dir / f"M_{rule}__BPROP_{bprop}_bt_histogram.png"
        _, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(
            m_values,
            stat="probability",
            ax=ax,
            color=rule_color_map[rule],
            edgecolor=None,
            binwidth=0.005,
            alpha=1,
        )

        ax.set_ylabel("")
        ax.set_xlim(0, 0.5)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=16)
        plt.savefig(
            output_file,
            bbox_inches="tight",
            dpi=300,
        )
        plt.close()

        output_file = bt_plots_dir / f"ASIN_{rule}__BPROP_{bprop}_bt_histogram.png"
        _, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(
            asin_data,
            stat="probability",
            ax=ax,
            color=rule_color_map[rule],
            edgecolor=None,
            binwidth=0.01,
            alpha=1,
        )

        ax.set_ylabel("")
        ax.set_xlim(0, 1.0)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=16)
        plt.savefig(
            output_file,
            bbox_inches="tight",
            dpi=300,
        )
        plt.close()

        output_file = bt_plots_dir / f"ODDS_{rule}__BPROP_{bprop}_bt_histogram.png"
        _, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(
            np.array(m_values) / (1 - np.array(m_values)),
            stat="probability",
            ax=ax,
            color=rule_color_map[rule],
            edgecolor=None,
            binwidth=0.01,
            alpha=1,
        )

        ax.set_ylabel("")
        ax.set_xlim(0, 1.0)
        ax.set_yticks([])
        ax.tick_params(axis="x", labelsize=16)
        plt.savefig(
            output_file,
            bbox_inches="tight",
            dpi=300,
        )
        plt.close()


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


if __name__ == "__main__":
    for rule in rule_color_map:
        # make_scottish_M_histogram(rule)
        make_bt_M_histograms(rule, [0.7])
        # make_legend()
