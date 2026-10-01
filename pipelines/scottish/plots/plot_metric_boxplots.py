"""Create consolidated Scottish boxplots across metrics and rules."""

import argparse
import sys
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.legend import Legend

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.scottish.plots._data import load_outputs_by_election_type
from voting_metrics_main_code.constants import (
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.constants import (
    RULE_LABELS,
    RULE_ORDER,
)
from voting_metrics_main_code.replication import ROOT

colors = [
    "#00B8D4",  # Borda
    "#fdbf6f",  # STV
    "#e31a1c",  # Plurality
    "#00cd99",  # 3-Approval
    "#b3de69",  # 2-Approval
    "#FF80AB",  # Ranked Pairs
    "#b2bac7",  # Random
    "#6200EA",
    "#f68eee",
    "#ffca5d",
    "#33a02c",
    "#FFEA00",
    "#ff7f00",
    "#B388FF",
    "#D81B60",
    "#0099cd",
    "#26A69A",
    "#00cd99",
    "#99cd00",
    "#cd0099",
    "#9900cd",
    "#8dd3c7",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
    "#ffffb3",
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#fb9a99",
    "#cab2d6",
    "#6a3d9a",
    "#b15928",
    "#64ffda",
    "#A1887F",
    "#76FF03",
    "#DCE775",
]


def construct_df_scottish(
    data_dictionary: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    n_cands: int,
    metric: str,
) -> pd.DataFrame:
    """Construct a DataFrame for a metric at a fixed candidate count.

    Args:
        data_dictionary (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Nested mapping of
            rule to candidate count to metric values.
        n_cands (int): Number of candidates to extract.
        metric (str): Metric key to select.

    Returns:
        pd.DataFrame: A transposed DataFrame with rules as columns.
    """
    df_data = []

    for _, data in data_dictionary.items():
        df_data.append(data[str(n_cands)][metric])

    return pd.DataFrame(df_data, index=list(data_dictionary)).T


def build_plot_for_metric_scottish(
    metric: str,
    ordered_outputs: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    n_cand_list: Sequence[int],
    ax: Axes,
    y_label: str = "",
    use_one: bool = False,
    legend: bool = True,
) -> Axes:
    """Build a boxplot for a single metric across candidate counts.

    Args:
        metric (str): Metric key to plot.
        ordered_outputs (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Nested mapping of
            rule to candidate count to metric values.
        n_cand_list (Sequence[int]): Candidate counts to include.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str, optional): Label for the y-axis. Defaults to ''.
        use_one (bool, optional): Whether to plot only the Borda rule. Defaults to False.
        legend (bool, optional): Whether to render a legend. Defaults to True.

    Returns:
        Axes: The axes with the plot.
    """
    df_list = []

    for n_cands in n_cand_list:
        df = construct_df_scottish(ordered_outputs, n_cands, metric)
        df = df.melt(var_name="rule", value_name="value")
        df["n_cands"] = n_cands

        df_list.append(df)

    if use_one:
        df_list = [df[df["rule"] == "borda"] for df in df_list]

    long = pd.concat(df_list, ignore_index=True)

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",  # σ_IIA values
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=legend,
        # Seaborn accepts percentile pairs; its stub only declares a float.
        whis=[1, 99],  # type: ignore[arg-type]
        saturation=1,
    )

    # ax.set_ylabel(y_label, fontsize=16)
    ax.set_ylim(-0.05, 1.05)
    # ax.set_xlabel("Number of candidates", fontsize=16)
    ax.set_xlabel("")
    ax.set_ylabel("")

    if not use_one and legend:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")

    return ax


def save_legend_only(
    legend: Legend,
    filename: str | Path,
    pad: float = 1.1,
    dpi: int = 300,
    transparent: bool = False,
) -> None:
    """Save a legend as a standalone image.

    Args:
        legend (Legend): Matplotlib legend to export.
        filename (str | Path): Path to write the legend image.
        pad (float, optional): Padding factor for legend bounds. Defaults to 1.1.
        dpi (int, optional): Output DPI. Defaults to 300.
        transparent (bool, optional): Whether to use a transparent background. Defaults to False.

    Raises:
        ValueError: The legend is not attached to a figure.
    """
    fig = legend.get_figure(root=True)

    if fig is None:
        raise ValueError("The legend must be attached to a figure before saving.")

    fig.canvas.draw()  # need a renderer before measuring bbox

    # legend bbox in display coords → inches
    bbox = legend.get_window_extent().expanded(pad, pad)
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, transparent=transparent)


def load_boxplot_metrics(
    ordered_rules: Sequence[str], *, stats_root: Path
) -> dict[str, dict[str, dict[str, list[float]]]]:
    """Load average and worst-case Scottish metric arrays with lexicographic tiebreaks.

    Args:
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        stats_root (Path): Parent of the dataset statistics directories.

    Returns:
        dict[str, dict[str, dict[str, list[float]]]]: Scores keyed by rule, candidate-count string,
            and metric key including the tiebreak suffix.
    """
    return load_outputs_by_election_type(
        stats_root / "scottish_stats", ordered_rules, tiebreaks=("lex",)
    )


def main(
    n_cand_list: Sequence[int] = list(range(6, 10)),
    *,
    stats_root: Path | None = None,
    output_root: Path = ROOT,
) -> None:
    """Run the Scottish boxplot pipeline and export plots.

    Args:
        n_cand_list (Sequence[int], optional): Candidate counts to include. Defaults to
            list(range(6, 10)).
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root. Defaults to None.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()
    print(f"Statistics: {stats_root}")
    print(f"Output root: {output_root}")

    ordered_rules = RULE_ORDER

    output_dir = str(output_root / "plots/scottish/scottish_sigma_plots_collected")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ==========================
    # Make the scottish boxplots
    # ==========================

    tiebreak = "lex"
    outputs_by_election_type = load_boxplot_metrics(ordered_rules, stats_root=stats_root)

    metric_label_pairs = [
        (f"sigma_UM_worst_case_asin_{tiebreak}", "$\\sigma_{UM}$ ranking"),
        (
            f"sigma_UM_winner_set_worst_case_asin_{tiebreak}",
            "$\\sigma_{UM}$ winner-set",
        ),
        (
            f"sigma_IIA_average_{tiebreak}",
            "$\\sigma_{IIA}$ ranking",
        ),
        (
            f"sigma_IIA_winner_set_average_{tiebreak}",
            "$\\sigma_{IIA}$ winner-set",
        ),
    ]

    # ==========================
    #         BOX PLOTS
    # ==========================

    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    for metric, label in metric_label_pairs:
        _, ax = plt.subplots(1, 1, figsize=(20, 6))
        ordered_outputs = {key: outputs_by_election_type[key] for key in ordered_rules}
        print(metric, label)
        build_plot_for_metric_scottish(
            metric,
            ordered_outputs,
            n_cand_list,
            ax,
            y_label=label,
            legend=False,
        )
        output_plot_name = f"{output_dir}/scottish_boxplot_{metric}_collected.png"

        plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

        plt.close()

    metric, label = metric_label_pairs[0]
    _, ax = plt.subplots(1, 1, figsize=(20, 6))
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    ordered_outputs = {key: outputs_by_election_type[key] for key in ordered_rules}
    ax = build_plot_for_metric_scottish(
        metric,
        ordered_outputs,
        n_cand_list,
        ax,
        y_label=label,
        legend=True,
    )

    legend = ax.get_legend()

    handles, labels = ax.get_legend_handles_labels()
    new_names = RULE_LABELS
    labels = [new_names[label] for label in labels]
    legend = ax.legend(handles, labels, title="Voting rule", loc=(1.02, 0.5))

    output_plot_name = f"{output_dir}/scottish_boxplot_legend.png"
    save_legend_only(legend, output_plot_name, pad=1.1, dpi=300, transparent=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(stats_root=args.stats_dir, output_root=args.output_dir)
