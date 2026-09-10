"""Plot six-rule Scottish metric boxplots and export tables from aggregate JSONs."""

import json
import sys
from glob import glob
from pathlib import Path
from typing import cast

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import NON_RANDOM_RULE_ORDER
from voting_metrics_main_code.replication import PLOTS_DIR, STATS_INPUT, STATS_OUTPUT


def construct_df_scottish(data_dictionary, n_cands, metric):
    """Construct a DataFrame for one metric at a fixed candidate count.

    Args:
        data_dictionary (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Mapping from rule
            to candidate-count string to metric key to score list.
        n_cands (int): Number of candidates.
        metric (str): Metric identifier used in the statistics filenames.

    Returns:
        pd.DataFrame: Score columns ordered by voting rule, with observations along the rows.
    """
    df_data = []

    for _, data in data_dictionary.items():
        df_data.append(data[str(n_cands)][metric])

    return pd.DataFrame(df_data, index=list(data_dictionary)).T


def build_plot_for_metric_scottish(
    metric, ordered_outputs, ordered_rules, n_cand_list, ax, y_label="", use_one=False
):
    """Build a boxplot for one metric across candidate counts and voting rules.

    Args:
        metric (str): Metric identifier used in the statistics filenames.
        ordered_outputs (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Metric score lists
            keyed by rule, candidate-count string, and metric key.
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        n_cand_list (Sequence[int]): Candidate counts to include, in display order.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str, optional): Label for the y-axis. Defaults to ''.
        use_one (bool, optional): Whether to show only the Borda rule. Defaults to False.
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

    palette = sns.color_palette("colorblind", len(ordered_rules))
    rule_color_map = dict(zip(ordered_rules, palette))

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",  # σ_IIA values
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=not use_one,  # don't show legend if only one rule
        # Seaborn accepts percentile pairs; its stub only declares a float.
        whis=[1, 99],  # type: ignore[arg-type]
    )

    ax.set_ylabel(y_label, fontsize=16)

    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


def export_aggregate_tables(
    stat_file_base_dir: str, ordered_rules, n_cand_list, variant: str, tiebreak: str
) -> None:
    """Export aggregate Scottish statistics ordered by rule and candidate count.

    Args:
        stat_file_base_dir (str): Base directory containing the metric JSON files.
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        n_cand_list (Sequence[int]): Candidate counts to include, in display order.
        variant (str): Variant token used in the output filename; input files are not filtered by
            it.
        tiebreak (str): Tiebreak token used in the output filename; input files are not filtered by
            it.
    """
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

    index = cast(pd.MultiIndex, df.index)
    df.index = index.set_levels(index.levels[1].astype(int), level="n_cands")

    df = df.reindex(
        pd.MultiIndex.from_product(
            [ordered_rules, n_cand_list],
            names=["rule", "n_cands"],
        ),
    )

    (STATS_OUTPUT / "scottish_stats").mkdir(parents=True, exist_ok=True)

    df.to_csv(f"{STATS_OUTPUT}/scottish_stats/scottish_stats_{variant}_{tiebreak}.csv")


@click.command()
@click.option("--variant", required=True)
@click.option("--tiebreak", required=True)
def main(variant, tiebreak, n_cand_list=list(range(6, 10))):
    """Save Scottish metric boxplots and export aggregate statistics for the selected labels.

    Args:
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        n_cand_list (Sequence[int], optional): Candidate counts to include, in display order.
            Defaults to list(range(6, 10)).
    """
    ordered_rules = NON_RANDOM_RULE_ORDER

    stat_file_base_dir = str(Path(f"{STATS_INPUT}/scottish_stats/").resolve())
    output_dir = f"{PLOTS_DIR}/scottish"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_plot_name = f"{str(output_dir)}/scottish_sigma_plots_{variant}_{tiebreak}.png"

    # ==========================
    # Make the scottish boxplots
    # ==========================
    all_output_files = glob(f"{STATS_INPUT}/scottish_stats/*output.json")

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
        (f"sigma_IIA_{variant}_{tiebreak}", "$\\sigma_{IIA}$ ranking"),
        (f"sigma_IIA_all_subset_{variant}_{tiebreak}", "$\\sigma_{IIA}$ subset"),
        (f"sigma_IIA_winner_set_{variant}_{tiebreak}", "$\\sigma_{IIA}$ winner-set"),
    ]
    fig, ax = plt.subplots(len(metric_label_pairs), 1, figsize=(20, 6 * len(metric_label_pairs)))
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
    export_aggregate_tables(stat_file_base_dir, ordered_rules, n_cand_list, variant, tiebreak)


if __name__ == "__main__":
    main()
