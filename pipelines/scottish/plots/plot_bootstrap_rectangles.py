"""Plot Bonferroni confidence rectangles from Scottish bootstrap interval tables."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import RULE_COLORS as rule_color_map
from voting_metrics_main_code.replication import PLOTS_DIR, SCOTTISH_BOOTSTRAP_INPUT


def plot_rectangles(df: pd.DataFrame, metric: str, rule_color_map: dict[str, str]):
    """
    Plot rectangles [um_L, um_U] x [iia_L, iia_U] for each row in df.

    Args:
        df (pd.DataFrame): DataFrame with columns 'um_L', 'um_U', 'iia_L', 'iia_U', 'rule'.
        rule_color_map (dict[str,str]): dict mapping rule names to colors.
    """
    fig, ax = plt.subplots(figsize=(8, 8), dpi=300)

    for idx, row in df.iterrows():
        x0 = row["um_L"]
        x1 = row["um_U"]
        y0 = row["iia_L"]
        y1 = row["iia_U"]
        rule = row["rule"]

        color = rule_color_map.get(rule, "black")

        rect = Rectangle(
            (x0, y0),  # lower-left corner
            x1 - x0,  # width
            y1 - y0,  # height
            facecolor=color,
            edgecolor=color,
            linewidth=2,
            alpha=1.0,
        )
        ax.add_patch(rect)

    ax.set_xticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xlim(0.56, 1.02)
    ax.set_ylim(0.47, 1.02)

    ax.tick_params(axis="both", which="major", labelsize=16)

    output_file = (
        PLOTS_DIR / "scottish" / "bonferroni_rectangles" / f"{metric}_bonferroni_rectangle_plot.png"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, bbox_inches="tight", dpi=300)


def main() -> None:

    df = pd.read_csv(
        SCOTTISH_BOOTSTRAP_INPUT
        / "bootstrap_rectangles_sigma_IIA_average_vs_sigma_UM_worst_case_asin.csv"
    )

    total_df = df.query("candidate_size.isna()")
    plot_rectangles(total_df, "rho_UM", rule_color_map)

    winner_df = pd.read_csv(
        SCOTTISH_BOOTSTRAP_INPUT
        / "bootstrap_rectangles_sigma_IIA_winner_set_average_vs_sigma_UM_winner_set_worst_case_asin.csv"
    )
    winner_total_df = winner_df.query("candidate_size.isna()")
    plot_rectangles(winner_total_df, "sigma_UM", rule_color_map)


if __name__ == "__main__":
    main()
