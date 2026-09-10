"""Plot Bonferroni confidence rectangles from Scottish bootstrap interval tables."""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import RULE_COLORS as rule_color_map
from voting_metrics_main_code.replication import ROOT


def plot_rectangles(
    df: pd.DataFrame, metric: str, rule_color_map: dict[str, str], *, output_root: Path
) -> None:
    """Plot rectangles [um_L, um_U] x [iia_L, iia_U] for each row in df.

    Args:
        output_root (Path): Run root containing stats, plots, and tables.
        df (pd.DataFrame): DataFrame with columns 'um_L', 'um_U', 'iia_L', 'iia_U', 'rule'.
        metric (str): Metric label used in the output filename.
        rule_color_map (dict[str, str]): dict mapping rule names to colors.
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
        output_root
        / "plots"
        / "scottish"
        / "bonferroni_rectangles"
        / f"{metric}_bonferroni_rectangle_plot.png"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_file, bbox_inches="tight", dpi=300)


def main(*, bootstrap_root: Path | None = None, output_root: Path = ROOT) -> None:
    """Save pooled bootstrap rectangle plots for ranking and winner-set metrics.

    Args:
        bootstrap_root (Path | None, optional): Directory containing bootstrap interval CSVs. None
            uses the selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    bootstrap_root = (bootstrap_root or output_root / "stats/scottish_stats/bootstrap").resolve()
    print(f"Bootstrap intervals: {bootstrap_root}")
    print(f"Output root: {output_root}")

    df = pd.read_csv(
        bootstrap_root / "bootstrap_rectangles_sigma_IIA_average_vs_sigma_UM_worst_case_asin.csv"
    )

    total_df = df.query("candidate_size.isna()")
    plot_rectangles(total_df, "rho_UM", rule_color_map, output_root=output_root)

    winner_df = pd.read_csv(
        bootstrap_root
        / "bootstrap_rectangles_sigma_IIA_winner_set_average_vs_sigma_UM_winner_set_worst_case_asin.csv"
    )
    winner_total_df = winner_df.query("candidate_size.isna()")
    plot_rectangles(winner_total_df, "sigma_UM", rule_color_map, output_root=output_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(bootstrap_root=args.bootstrap_dir, output_root=args.output_dir)
