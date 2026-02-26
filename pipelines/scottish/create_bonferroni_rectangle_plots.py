import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
import pandas as pd

rule_color_map = {
    "borda": "#1460bc",         # denim
    "3-approval": "#8cb500",    # applegreen
    "2-approval": "#218c21",    # forestgreen
    "plurality": "#d11942",     # alizarin
    "stv": "#ffc40c",           # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",        # slategray
}

TOP_DIR = Path(__file__).resolve().parents[2]


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
            (x0, y0),           # lower-left corner
            x1 - x0,            # width
            y1 - y0,            # height
            facecolor=color,
            edgecolor=color,
            linewidth=2,
            alpha=1.0
        )
        ax.add_patch(rect)


    # Auto-set limits with a little padding
    x_min = df["um_L"].min()
    x_max = df["um_U"].max()
    y_min = df["iia_L"].min()
    y_max = df["iia_U"].max()

    x_pad = 0.02 * (x_max - x_min if x_max > x_min else 1)
    y_pad = 0.02 * (y_max - y_min if y_max > y_min else 1)

    ax.set_xticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xlim(0.56, 1.02)
    ax.set_ylim(0.47, 1.02)

    ax.tick_params(axis='both', which='major', labelsize=16)

    output_file = TOP_DIR / "plots" / "scottish" / "bonferroni_rectangles" /f"{metric}_bonferroni_rectangle_plot.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, bbox_inches="tight", dpi=300)

    
if __name__ == "__main__":
    
    df = pd.read_csv(TOP_DIR / "stats/scottish_stats/bootstrap/bootstrap_rectangles_sigma_IIA_average_vs_sigma_UM_worst_case_asin.csv")

    total_df = df.query("candidate_size.isna()")
    plot_rectangles(total_df, "rho_UM", rule_color_map)

    winner_df = pd.read_csv(TOP_DIR / "stats/scottish_stats/bootstrap/bootstrap_rectangles_sigma_IIA_winner_set_average_vs_sigma_UM_winner_set_worst_case_asin.csv")
    winner_total_df = winner_df.query("candidate_size.isna()")
    plot_rectangles(winner_total_df, "sigma_UM", rule_color_map)