"""Create consolidated Scottish boxplots across metrics and rules."""

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
    RULE_LABELS,
    RULE_ORDER,
)
from voting_metrics_main_code.replication import PLOTS_DIR, STATS_INPUT

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

# rule_color_map = {
#     "borda": "#00B8D4",
#     "3-approval": "#00cd99",
#     "2-approval": "#b3de69",
#     "plurality": "#e31a1c",
#     "stv": "#fdbf6f",
#     "ranked-pairs": "#FF80AB",
#     "random": "#b2bac7",
# }


# \definecolor{applegreen}{rgb}{0.55, 0.71, 0.0} #"#8cb500"
# \definecolor{alizarin}{rgb}{0.82, 0.1, 0.26} #"#d11942"
# \definecolor{slategray}{rgb}{0.44, 0.5, 0.56} #"#707f8e"
# \definecolor{amber}{rgb}{1.0, 0.75, 0.0} #"#ffbf00"
# \definecolor{mikadoyellow}{rgb}{1.0, 0.77, 0.05} #"#ffc40c"
# \definecolor{cadmiumgreen}{rgb}{0.0, 0.42, 0.24} #"#006b3d"
# \definecolor{forestgreen}{rgb}{0.13, 0.55, 0.13} #"#218c21"
# \definecolor{lust}{rgb}{0.9, 0.13, 0.13} #"#e52121"
# \definecolor{denim}{rgb}{0.08, 0.38, 0.74} #"#1460bc"
# \definecolor{purpleheart}{rgb}{0.41, 0.21, 0.61} #"#68359b"
# \definecolor{cherryblossompink}{rgb}{1.0, 0.72, 0.77} #"#ffb7c4"
# \definecolor{darktangerine}{rgb}{1.0, 0.66, 0.07} #"#ffa811"
# \definecolor{bananayellow}{rgb}{1.0, 0.88, 0.21} #"#ffe035"
# \definecolor{lightblue}{rgb}{0.55,0.82,0.77} #"#8cd1c4"

# "#8cb500"
# "#d11942"
# "#707f8e"
# "#ffbf00"
# "#ffc40c"
# "#006b3d"
# "#218c21"
# "#e52121"
# "#1460bc"
# "#68359b"
# "#ffb7c4"
# "#ffa811"
# "#ffe035"
# "#8cd1c4


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

    return pd.DataFrame(df_data, index=data_dictionary.keys()).T  # ty: ignore


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
        whis=[1, 99],  # use 1st and 99th percentiles # type: ignore
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
    """
    fig = legend.axes.figure  # the parent figure
    fig.canvas.draw()  # need a renderer before measuring bbox

    # legend bbox in display coords → inches
    bbox = legend.get_window_extent().expanded(pad, pad)
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, transparent=transparent)  # ty: ignore


def load_boxplot_metrics(ordered_rules: Sequence[str]):
    """Load average and worst-case Scottish metric arrays with lexicographic tiebreaks.

    Args:
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.

    Returns:
        dict[str, dict[str, dict[str, list[float]]]]: Scores keyed by rule, candidate-count string,
            and metric key including the tiebreak suffix.
    """
    return load_outputs_by_election_type(
        STATS_INPUT / "scottish_stats", ordered_rules, tiebreaks=("lex",)
    )


def main(n_cand_list: Sequence[int] = list(range(6, 10))) -> None:
    """Run the Scottish boxplot pipeline and export plots.

    Args:
        n_cand_list (Sequence[int], optional): Candidate counts to include. Defaults to
            list(range(6, 10)).
    """
    ordered_rules = RULE_ORDER

    output_dir = f"{PLOTS_DIR}/scottish/scottish_sigma_plots_collected"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ==========================
    # Make the scottish boxplots
    # ==========================

    tiebreak = "lex"
    outputs_by_election_type = load_boxplot_metrics(ordered_rules)

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
    main()
