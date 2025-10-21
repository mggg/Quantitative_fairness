from pathlib import Path
from glob import glob
from itertools import product
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from metric_lists import (
    iia_metric_list,
    um_metric_list,
)

rule_color_map = {
    "borda": "#1460bc",  # lightblue
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}


script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()
plots_dir = top_dir / "plots" / "bt_plots" / "b_bloc_sweep_boxplots"


def save_legend_only(legend, filename, pad=1.1, dpi=300, transparent=False):
    fig = legend.axes.figure  # the parent figure
    fig.canvas.draw()  # need a renderer before measuring bbox

    # legend bbox in display coords → inches
    bbox = legend.get_window_extent().expanded(pad, pad)
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, transparent=transparent)


def build_plot_for_metric(rule_to_data_dict, ax, rule_color_map=None, legend=False):
    df = pd.DataFrame.from_dict(rule_to_data_dict)
    long = df.melt(var_name="rule", value_name="score")
    long["group"] = ""  # single x category

    sns.boxplot(
        data=long,
        x="group",
        y="score",
        hue="rule",
        ax=ax,
        palette=rule_color_map,
        whis=[1, 99],
        dodge=True,
        legend=legend,
    )
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticks([])  # hide x-axis ticks
    ax.set_xticklabels([])  # hide x-axis labels

    if legend:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")

    return ax


b_bloc_proportions = [0.5, 0.6, 0.7, 0.8, 0.9]
voting_rule_list = ["borda", "stv", "plurality"]

variant = "average"
tiebreak = "lex"
for metric, b_prop in product(iia_metric_list, b_bloc_proportions):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}_b-bloc_prop_{b_prop}_boxplot.png"

    voting_rule_to_data = {}

    for voting_rule in voting_rule_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_None"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{b_prop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = []
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points.extend(data)

        voting_rule_to_data[voting_rule] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    build_plot_for_metric(
        voting_rule_to_data,
        ax=ax,
        rule_color_map=rule_color_map,
    )

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()

variant = "worst_case"
for metric, b_prop in product(um_metric_list, b_bloc_proportions):
    plots_dir.mkdir(parents=True, exist_ok=True)
    output_file = plots_dir / f"{metric}__{variant}_b-bloc_prop_{b_prop}_boxplot.png"

    voting_rule_to_data = {}

    for voting_rule in voting_rule_list:
        file_basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_asin"
            f"__NCANDS_(*)"
            f"__SEATS_3"
            f"__BPROP_{b_prop}"
            f"__ALPHA_(*)"
            f"__COHESION_(*)"
            f"__TYPE_{voting_rule}"
            f"__TIEBREAK_{tiebreak}"
        )

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
        )

        data_points = []
        for i, file in enumerate(all_files):
            with open(file, "r") as f:
                data = json.load(f)

            data_points.extend(data)

        voting_rule_to_data[voting_rule] = np.array(data_points)

    fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

    build_plot_for_metric(
        voting_rule_to_data,
        ax=ax,
        rule_color_map=rule_color_map,
    )

    plt.savefig(
        output_file,
        bbox_inches="tight",
        dpi=300,
    )
    plt.close()

metric = um_metric_list[0]
b_prop = b_bloc_proportions[0]
plots_dir.mkdir(parents=True, exist_ok=True)

voting_rule_to_data = {}

for voting_rule in voting_rule_list:
    file_basename = (
        f"METRIC_{metric}"
        f"__VARIANT_{variant}"
        f"__INTERP_asin"
        f"__NCANDS_(*)"
        f"__SEATS_3"
        f"__BPROP_{b_prop}"
        f"__ALPHA_(*)"
        f"__COHESION_(*)"
        f"__TYPE_{voting_rule}"
        f"__TIEBREAK_{tiebreak}"
    )

    all_files = glob(
        f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{file_basename}.json"
    )

    data_points = []
    for i, file in enumerate(all_files):
        with open(file, "r") as f:
            data = json.load(f)

        data_points.extend(data)

    voting_rule_to_data[voting_rule] = np.array(data_points)


# Just saving the legend as well
fig, ax = plt.subplots(figsize=(20, 20), dpi=300)

ax = build_plot_for_metric(
    voting_rule_to_data,
    ax=ax,
    rule_color_map=rule_color_map,
)
legend = ax.get_legend()

handles, labels = ax.get_legend_handles_labels()
new_names = {
    "borda": "Borda",
    "plurality": "Plurality",
    "stv": "STV",
}
labels = [new_names[label] for label in labels]
legend = ax.legend(handles, labels, title="Voting rule", loc=(1.02, 0.5))

output_plot_name = f"{plots_dir}/boxplot_legend.png"
save_legend_only(legend, output_plot_name, pad=1.1, dpi=300, transparent=False)

plt.close()
