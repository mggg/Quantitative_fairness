import json
from glob import glob
import math
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

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


def inverse_interp(x):
    return math.sin((math.pi / 2) * x) ** 2 / 2


def make_scottish_M_histogram(rule):
    file = glob(
        f"{top_dir}/stats/scottish_stats/sigma_UM_worst_case_asin/**/*{rule}*lex_output.json",
        recursive=True,
    )[0]

    output_file = scottish_plots_dir / f"M_{rule}_scottish_histogram.png"
    with open(file, "r") as f:
        data = json.load(f)

    m_values = []
    for n_cands, val_dict in data.items():
        for file, rho_um in val_dict.items():
            if rho_um < 1.0:
                m_values.append(inverse_interp(rho_um))
    _, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(
        m_values,
        stat="probability",
        ax=ax,
        color=rule_color_map[rule],
        edgecolor=None,
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


def make_bt_M_histograms(rule):
    if rule == "random":
        return

    for bprop in [0.5, 0.6, 0.7, 0.8, 0.9]:
        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/sigma_UM/**/{rule}/"
            f"METRIC_sigma_UM__VARIANT_worst_case__INTERP_asin__*BPROP_{bprop}*TIEBREAK_lex.json"
        )

        m_values = []
        asin_data = []
        for file in all_files:
            with open(file, "r") as f:
                data = json.load(f)

            for rho_um in data:
                if rho_um < 1.0:
                    asin_data.append(rho_um)
                    m_values.append(inverse_interp(rho_um))

        output_file = bt_plots_dir / f"M_{rule}__BPROP_{bprop}_bt_histogram.png"
        _, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(
            m_values,
            stat="probability",
            ax=ax,
            color=rule_color_map[rule],
            edgecolor=None,
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


if __name__ == "__main__":
    for rule in rule_color_map:
        make_scottish_M_histogram(rule)
        make_bt_M_histograms(rule)
