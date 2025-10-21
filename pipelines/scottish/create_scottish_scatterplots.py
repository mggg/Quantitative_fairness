import matplotlib.pyplot as plt
from itertools import product
import json
from glob import glob
import seaborn as sns
import pandas as pd
from pathlib import Path

rule_color_map = {
    "borda": "#00B8D4",  # bright cerulean
    "3-approval": "#00cd99",  # mint
    "2-approval": "#b3de69",  # pale olive
    "plurality": "#e31a1c",  # cadmium
    "stv": "#fdbf6f",  # saffron mango
    "ranked-pairs": "#FF80AB",  # rose
    "random": "#b2bac7",  # casper grey
}

rule_color_map = {
    "borda": "#8cd1c4",  # lightblue
    "3-approval": "#218c21",  # forestgreen
    "2-approval": "#8cb500",  # applegreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}

rule_color_map = {
    "borda": "#007f7f",  # teal
    "3-approval": "#218c21",  # forestgreen
    "2-approval": "#8cb500",  # applegreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}
rule_color_map = {
    "borda": "#1460bc",  # denim
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}
titles = {
    "borda": "Borda",
    "3-approval": "3-Approval",
    "2-approval": "2-Approval",
    "plurality": "Plurality",
    "stv": "STV",
    "ranked-pairs": "Ranked Pairs",
    "random": "Random",
}


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
    metric, ordered_outputs, ordered_rules, n_cand_list, ax, y_label="", use_one=False
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
        legend=not use_one,  # don't show legend if only one rule
        whis=[1, 99],  # use 1st and 99th percentiles
    )

    ax.set_ylabel(y_label, fontsize=16)
    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


def main():
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
    output_dir = f"{top_dir}/plots/scottish"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ==========================
    # Make the scottish boxplots
    # ==========================

    all_output_files = glob(
        f"{top_dir}/stats/scottish_stats_newr_but_still_old/*output.json"
    )

    outputs_by_election_type = {}
    for output_file in all_output_files:
        with open(output_file, "r") as f:
            output = json.load(f)
        election_type = output_file.split("/")[-1].split("_")[0]
        output_dict = {
            n_cands: {
                metric: list(file_values_dict.values())
                for metric, file_values_dict in metric_values_dict.items()
            }
            for n_cands, metric_values_dict in output.items()
        }
        outputs_by_election_type[election_type] = output_dict

    election_type_to_metric_to_cand_count = {}
    n_cand_set = set()

    for variant, tiebreak, voting_rule in product(
        ["average", "worst_case"], ["lex", "random"], ordered_rules
    ):
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
                # print(f"setting {election_type} {n_cands} {metric}")

    # ==========================
    #       SCATTER PLOTS
    # ==========================

    # for variant1, variant2, tiebreak in product(
    #     ["average", "worst_case"], ["average", "worst_case"], ["lex", "random"]
    # ):
    #     um_ranking = [
    #         (f"sigma_UM_{variant1}_odds_{tiebreak}", "$\\sigma_{UM}$ ranking ODDS"),
    #         (f"sigma_UM_{variant1}_asin_{tiebreak}", "$\\sigma_{UM}$ ranking ASIN"),
    #     ]

    #     um_winner_set = [
    #         (
    #             f"sigma_UM_winner_set_{variant1}_odds_{tiebreak}",
    #             "$\\sigma_{UM}$ winner-set ODDS",
    #         ),
    #         (
    #             f"sigma_UM_winner_set_{variant1}_asin_{tiebreak}",
    #             "$\\sigma_{UM}$ winner-set ASIN",
    #         ),
    #     ]

    #     iia_ranking = [
    #         (f"sigma_IIA_{variant2}_{tiebreak}", "$\\sigma_{IIA}$ ranking single"),
    #         (
    #             f"sigma_IIA_all_subset_{variant2}_{tiebreak}",
    #             "$\\sigma_{IIA}$ ranking all subset",
    #         ),
    #     ]

    #     iia_winner_set = [
    #         (
    #             f"sigma_IIA_winner_set_{variant2}_{tiebreak}",
    #             "$\\sigma_{IIA}$ winner-set single",
    #         ),
    #         (
    #             f"sigma_IIA_winner_set_all_subset_{variant2}_{tiebreak}",
    #             "$\\sigma_{IIA}$ winner-set all subset",
    #         ),
    #     ]

    #     for voting_rule in ordered_rules:
    #         for (um_key, um_label), (iia_key, iia_label) in product(
    #             um_ranking, iia_ranking
    #         ):
    #             scatter_dir = f"{output_dir}/scatter/um-{variant1}_iia-{variant2}"
    #             Path(scatter_dir).mkdir(parents=True, exist_ok=True)
    #             plot_name = (
    #                 f"{scatter_dir}/{voting_rule}_{um_key}_vs_{iia_key}_scatter.png"
    #             )
    #             fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    #             sns.set_theme(
    #                 style="ticks", context="notebook", font="serif", font_scale=1.2
    #             )
    #             x_data = []
    #             for n_cands, data in outputs_by_election_type[voting_rule].items():
    #                 x_data.extend(data[um_key])

    #             y_data = []
    #             for n_cands, data in outputs_by_election_type[voting_rule].items():
    #                 y_data.extend(data[iia_key])

    #             ax.scatter(x_data, y_data, color=rule_color_map[voting_rule])
    #             ax.set_xlim(-0.05, 1.05)
    #             ax.set_ylim(-0.05, 1.05)
    #             plt.title(f"{voting_rule}", fontsize=20)
    #             plt.xlabel(um_label, fontsize=16)
    #             plt.ylabel(iia_label, fontsize=16)
    #             plt.savefig(plot_name, bbox_inches="tight", dpi=300)

    #             plt.close(fig)

    #         for (um_key, um_label), (iia_key, iia_label) in product(
    #             um_winner_set, iia_winner_set
    #         ):
    #             scatter_dir = f"{output_dir}/scatter/umws-{variant1}_iiaws-{variant2}"
    #             Path(scatter_dir).mkdir(parents=True, exist_ok=True)
    #             plot_name = (
    #                 f"{scatter_dir}/{voting_rule}_{um_key}_vs_{iia_key}_scatter.png"
    #             )
    #             fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    #             sns.set_theme(
    #                 style="ticks", context="notebook", font="serif", font_scale=1.2
    #             )
    #             x_data = []
    #             for n_cands, data in outputs_by_election_type[voting_rule].items():
    #                 x_data.extend(data[um_key])

    #             y_data = []
    #             for n_cands, data in outputs_by_election_type[voting_rule].items():
    #                 y_data.extend(data[iia_key])

    #             ax.scatter(x_data, y_data, color=rule_color_map[voting_rule])
    #             ax.set_xlim(-0.05, 1.05)
    #             ax.set_ylim(-0.05, 1.05)
    #             plt.title(f"{titles[voting_rule]}", fontsize=20)
    #             plt.xlabel(um_label, fontsize=16)
    #             plt.ylabel(iia_label, fontsize=16)
    #             plt.savefig(plot_name, bbox_inches="tight", dpi=300)

    #             plt.close(fig)

    # =========================
    #   LIMITED SCATTER PLOTS
    # =========================

    variant1 = "worst_case"
    variant2 = "average"
    tiebreak = "lex"
    um_ranking = [
        (f"sigma_UM_{variant1}_asin_{tiebreak}", "$\\sigma_{UM}$ ranking ASIN"),
    ]

    um_winner_set = [
        (
            f"sigma_UM_winner_set_{variant1}_asin_{tiebreak}",
            "$\\sigma_{UM}$ winner-set ASIN",
        ),
    ]

    iia_ranking = [
        (f"sigma_IIA_{variant2}_{tiebreak}", "$\\sigma_{IIA}$ ranking single"),
    ]

    iia_winner_set = [
        (
            f"sigma_IIA_winner_set_{variant2}_{tiebreak}",
            "$\\sigma_{IIA}$ winner-set single",
        ),
    ]

    for voting_rule in ordered_rules:
        for (um_key, um_label), (iia_key, iia_label) in product(
            um_ranking, iia_ranking
        ):
            scatter_dir = f"{output_dir}/scatter_by_voting_rule"
            Path(scatter_dir).mkdir(parents=True, exist_ok=True)
            plot_name = (
                f"{scatter_dir}/"
                f"{voting_rule}_"
                f"{um_key.removesuffix(f'_{variant1}_asin_{tiebreak}')}_vs_"
                f"{iia_key.removesuffix(f'_{variant2}_{tiebreak}')}_scatter.png"
            )
            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
            sns.set_theme(
                style="ticks", context="notebook", font="serif", font_scale=1.2
            )
            x_data = []
            for n_cands, data in outputs_by_election_type[voting_rule].items():
                x_data.extend(data[um_key])

            y_data = []
            for n_cands, data in outputs_by_election_type[voting_rule].items():
                y_data.extend(data[iia_key])

            ax.scatter(x_data, y_data, color=rule_color_map[voting_rule])
            ax.set_xlim(-0.05, 1.05)
            ax.set_ylim(-0.05, 1.05)
            ax.vlines(
                0.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.vlines(
                1.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.hlines(
                0.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.hlines(
                1.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )

            plt.savefig(plot_name, bbox_inches="tight", dpi=300)

            plt.close(fig)

        for (um_key, um_label), (iia_key, iia_label) in product(
            um_winner_set, iia_winner_set
        ):
            scatter_dir = f"{output_dir}/scatter_by_voting_rule"
            Path(scatter_dir).mkdir(parents=True, exist_ok=True)
            plot_name = (
                f"{scatter_dir}/"
                f"{voting_rule}_"
                f"{um_key.removesuffix(f'_{variant1}_asin_{tiebreak}')}_vs_"
                f"{iia_key.removesuffix(f'_{variant2}_{tiebreak}')}_scatter.png"
            )
            fig, ax = plt.subplots(1, 1, figsize=(8, 8))
            sns.set_theme(
                style="ticks", context="notebook", font="serif", font_scale=1.2
            )
            x_data = []
            for n_cands, data in outputs_by_election_type[voting_rule].items():
                x_data.extend(data[um_key])

            y_data = []
            for n_cands, data in outputs_by_election_type[voting_rule].items():
                y_data.extend(data[iia_key])

            ax.scatter(x_data, y_data, color=rule_color_map[voting_rule])
            ax.set_xlim(-0.05, 1.05)
            ax.set_ylim(-0.05, 1.05)
            ax.vlines(
                0.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.vlines(
                1.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.hlines(
                0.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )
            ax.hlines(
                1.0,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )

            plt.savefig(plot_name, bbox_inches="tight", dpi=300)

            plt.close(fig)


if __name__ == "__main__":
    main()
