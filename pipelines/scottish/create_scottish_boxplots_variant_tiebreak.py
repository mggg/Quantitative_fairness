"""Create Scottish boxplots split by variant and tiebreak."""

from glob import glob
import json
from pathlib import Path
from typing import Mapping, Sequence

import click
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import seaborn as sns

rule_color_map = {
    "borda": "#00B8D4",
    "3-approval": "#00cd99",
    "2-approval": "#b3de69",
    "plurality": "#e31a1c",
    "stv": "#fdbf6f",
    "ranked-pairs": "#FF80AB",
    "random": "#b2bac7",
}


def construct_df_scottish(
    data_dictionary: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    n_cands: int,
    metric: str,
) -> pd.DataFrame:
    """Construct a DataFrame for a metric at a fixed candidate count.

    Args:
        data_dictionary (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested mapping of rule to candidate count to metric values.
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
    ordered_rules: Sequence[str],
    n_cand_list: Sequence[int],
    ax: Axes,
    y_label: str = "",
    use_one: bool = False,
) -> None:
    """Build a boxplot for a single metric across candidate counts.

    Args:
        metric (str): Metric key to plot.
        ordered_outputs (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested mapping of rule to candidate count to metric values.
        ordered_rules (Sequence[str]): Ordered list of rules (for stable plotting).
        n_cand_list (Sequence[int]): Candidate counts to include.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str): Label for the y-axis.
        use_one (bool): Whether to plot only the Borda rule.
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
        whis=[1, 99],  # use 1st and 99th percentiles # ty: ignore
    )

    ax.set_ylabel(y_label, fontsize=16)
    ax.set_ylim(-0.1, 1.1)
    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


@click.command()
@click.option("--variant", required=True)
@click.option("--tiebreak", required=True)
def main(
    variant: str,
    tiebreak: str,
    n_cand_list: Sequence[int] = list(range(6, 10)),
) -> None:
    """Run the Scottish boxplot pipeline for a variant/tiebreak.

    Args:
        variant (str): Metric variant to plot (e.g., average or worst_case).
        tiebreak (str): Tiebreak rule to plot (e.g., lex or random).
        n_cand_list (Sequence[int]): Candidate counts to include.
    """
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
    stat_file_base_dir = str(Path(f"{top_dir}/stats/scottish_stats/").resolve())
    output_dir = f"{top_dir}/plots/scottish"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_plot_name = (
        f"{str(output_dir)}/scottish_sigma_plots_{variant}_{tiebreak}.png"
    )

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
                # print(f"setting {election_type} {n_cands} {metric}")

    metric_label_pairs = [
        (f"sigma_UM_{variant}_odds_{tiebreak}", "$\\sigma_{UM}$ ranking ODDS"),
        (f"sigma_UM_{variant}_asin_{tiebreak}", "$\\sigma_{UM}$ ranking ASIN"),
        (
            f"sigma_UM_winner_set_{variant}_odds_{tiebreak}",
            "$\\sigma_{UM}$ winner-set ranking ODDS",
        ),
        (
            f"sigma_UM_winner_set_{variant}_asin_{tiebreak}",
            "$\\sigma_{UM}$ winner-set ranking ASIN",
        ),
        (f"sigma_IIA_{variant}_{tiebreak}", "$\\sigma_{IIA}$ ranking single"),
        (
            f"sigma_IIA_all_subset_{variant}_{tiebreak}",
            "$\\sigma_{IIA}$ ranking all subset",
        ),
        (
            f"sigma_IIA_winner_set_{variant}_{tiebreak}",
            "$\\sigma_{IIA}$ winner-set single",
        ),
        (
            f"sigma_IIA_winner_set_all_subset_{variant}_{tiebreak}",
            "$\\sigma_{IIA}$ winner-set all subset",
        ),
    ]

    # ==========================
    #         BOX PLOTS
    # ==========================

    _, ax = plt.subplots(
        len(metric_label_pairs), 1, figsize=(20, 6 * len(metric_label_pairs))
    )
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    ordered_outputs = {key: outputs_by_election_type[key] for key in ordered_rules}
    for i, (metric, label) in enumerate(metric_label_pairs):
        build_plot_for_metric_scottish(
            metric,
            ordered_outputs,
            ordered_rules,
            n_cand_list,
            ax[i],
            y_label=label,
            use_one=(metric == "n_voters"),
        )

    plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

    # ===========================
    # Make the scottish stats csv
    # ===========================
    all_stats_files = glob(f"{stat_file_base_dir}/*stats.json")

    stats_by_type = {}
    for stats_file in all_stats_files:
        with open(stats_file, "r") as f:
            stats = json.load(f)
        election_type = stats_file.split("/")[-1].split("_")[0]
        stats_by_type[election_type] = stats

    df = pd.concat(
        {rule: pd.DataFrame(sub).T for rule, sub in stats_by_type.items()},
        names=["rule", "n_cands"],  # names for the new index levels
    )

    df.index = df.index.set_levels(df.index.levels[1].astype(int), level="n_cands")

    df = df.reindex(
        pd.MultiIndex.from_product(
            [ordered_rules, n_cand_list],  # ty: ignore
            names=["rule", "n_cands"],
        ),
    )

    df.to_csv(f"{stat_file_base_dir}/scottish_stats_{variant}_{tiebreak}.csv")


if __name__ == "__main__":
    main()
