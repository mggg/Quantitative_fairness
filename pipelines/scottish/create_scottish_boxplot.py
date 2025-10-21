import matplotlib.pyplot as plt
import json
from glob import glob
import seaborn as sns
import pandas as pd
from pathlib import Path

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

rule_color_map = {
    "borda": "#1460bc",  # lightblue
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}

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


def construct_df_scottish(data_dictionary, n_cands, metric):
    """
    Helper function to construct a DataFrame from the data dictionary.
    Included to improve readability.
    """
    df_data = []
    for _, data in data_dictionary.items():
        df_data.append(data[str(n_cands)][metric])

    return pd.DataFrame(df_data, index=data_dictionary.keys()).T


def build_plot_for_metric_scottish(
    metric,
    ordered_outputs,
    n_cand_list,
    ax,
    y_label="",
    use_one=False,
    legend=True,
):
    """
    Helper function to build a boxplot for a given metric.
    Included to improve readability.
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
    )

    # ax.set_ylabel(y_label, fontsize=16)
    ax.set_ylim(-0.05, 1.05)
    # ax.set_xlabel("Number of candidates", fontsize=16)
    ax.set_xlabel("")
    ax.set_ylabel("")
    if not use_one and legend:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")

    return ax


def save_legend_only(legend, filename, pad=1.1, dpi=300, transparent=False):
    fig = legend.axes.figure  # the parent figure
    fig.canvas.draw()  # need a renderer before measuring bbox

    # legend bbox in display coords → inches
    bbox = legend.get_window_extent().expanded(pad, pad)
    bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())

    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, transparent=transparent)


def main(n_cand_list=list(range(6, 10))):
    ordered_rules = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]

    top_dir = str(Path(__file__).resolve().parents[2])
    output_dir = f"{top_dir}/plots/scottish/scottish_sigma_plots_collected"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ==========================
    # Make the scottish boxplots
    # ==========================

    election_type_to_metric_to_cand_count = {}
    n_cand_set = set()

    tiebreak = "lex"
    for variant in ["average", "worst_case"]:
        for voting_rule in ordered_rules:
            all_output_files = glob(
                f"{top_dir}/stats/scottish_stats/*{variant}*/{voting_rule}/*{tiebreak}_output.json"
            )
            metric_to_values = {}
            for output_file in all_output_files:
                with open(output_file, "r") as f:
                    output = json.load(f)
                splits = output_file.split("/")[-1].split("__")
                metric = splits[0].removeprefix("METRIC_")
                election_type = splits[1].removeprefix("ELECTION_TYPE_").split("_")[0]
                metric_to_values[f"{metric}_{tiebreak}"] = {
                    k: list(v.values()) for k, v in output.items()
                }
                n_cand_set.update(set(output.keys()))

            if election_type not in election_type_to_metric_to_cand_count:
                election_type_to_metric_to_cand_count[election_type] = {}
            election_type_to_metric_to_cand_count[election_type] |= metric_to_values

    outputs_by_election_type = {}
    for (
        election_type,
        metric_to_cand_count,
    ) in election_type_to_metric_to_cand_count.items():
        if election_type not in outputs_by_election_type:
            outputs_by_election_type[election_type] = {}
        for metric, cand_count_to_values in metric_to_cand_count.items():
            for n_cands, value_list in cand_count_to_values.items():
                if n_cands not in outputs_by_election_type[election_type]:
                    outputs_by_election_type[election_type][n_cands] = {}
                outputs_by_election_type[election_type][n_cands][metric] = value_list

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

    # _, ax = plt.subplots(
    #     len(metric_label_pairs), 1, figsize=(20, 6 * len(metric_label_pairs))
    # )
    # sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    # ordered_outputs = {key: outputs_by_election_type[key] for key in ordered_rules}
    # for i, (metric, label) in enumerate(metric_label_pairs):
    #     build_plot_for_metric_scottish(
    #         metric,
    #         ordered_outputs,
    #         n_cand_list,
    #         ax[i],
    #         y_label=label,
    #         use_one=(metric == "n_voters"),
    #     )

    # plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

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

    # metric, label = metric_label_pairs[0]
    # _, ax = plt.subplots(1, 1, figsize=(20, 6))
    # sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    # ordered_outputs = {key: outputs_by_election_type[key] for key in ordered_rules}
    # ax = build_plot_for_metric_scottish(
    #     metric,
    #     ordered_outputs,
    #     n_cand_list,
    #     ax,
    #     y_label=label,
    #     legend=True,
    # )

    # legend = ax.get_legend()

    # handles, labels = ax.get_legend_handles_labels()
    # new_names = {
    #     "borda": "Borda",
    #     "3-approval": "3-Approval",
    #     "2-approval": "2-Approval",
    #     "plurality": "Plurality",
    #     "stv": "STV",
    #     "ranked-pairs": "Ranked Pairs",
    #     "random": "Random",
    # }
    # labels = [new_names[label] for label in labels]
    # legend = ax.legend(handles, labels, title="Voting rule", loc=(1.02, 0.5))

    # output_plot_name = f"{output_dir}/scottish_boxplot_legend.png"
    # save_legend_only(legend, output_plot_name, pad=1.1, dpi=300, transparent=False)


if __name__ == "__main__":
    main()
