"""Create Scottish boxplots split by variant and tiebreak."""

import json
import sys
from glob import escape, glob
from pathlib import Path
from typing import Mapping, Sequence, cast

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.scottish.plots._data import load_outputs_by_election_type
from voting_metrics_main_code.constants import RULE_ORDER
from voting_metrics_main_code.replication import ROOT

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
    ordered_rules: Sequence[str],
    n_cand_list: Sequence[int],
    ax: Axes,
    y_label: str = "",
    use_one: bool = False,
) -> None:
    """Build a boxplot for a single metric across candidate counts.

    Args:
        metric (str): Metric key to plot.
        ordered_outputs (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Nested mapping of
            rule to candidate count to metric values.
        ordered_rules (Sequence[str]): Ordered list of rules (for stable plotting).
        n_cand_list (Sequence[int]): Candidate counts to include.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str, optional): Label for the y-axis. Defaults to ''.
        use_one (bool, optional): Whether to plot only the Borda rule. Defaults to False.
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
        # Seaborn accepts percentile pairs; its stub only declares a float.
        whis=[1, 99],  # type: ignore[arg-type]
    )

    ax.set_ylabel(y_label, fontsize=16)
    ax.set_ylim(-0.1, 1.1)

    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


def export_aggregate_tables(
    stat_file_base_dir: str,
    ordered_rules: Sequence[str],
    n_cand_list: Sequence[int],
    variant: str,
    tiebreak: str,
    *,
    output_root: Path,
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
        output_root (Path): Run root containing stats, plots, and tables.
    """
    all_stats_files = glob(f"{escape(stat_file_base_dir)}/*stats.json")

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
            [list(ordered_rules), list(n_cand_list)],
            names=["rule", "n_cands"],
        ),
    )

    (output_root / "stats" / "scottish_stats").mkdir(parents=True, exist_ok=True)

    df.to_csv(f"{(output_root / 'stats')}/scottish_stats/scottish_stats_{variant}_{tiebreak}.csv")


@click.command()
@click.option("--variant", required=True)
@click.option("--tiebreak", required=True)
@click.option(
    "--stats-dir",
    "stats_root",
    type=click.Path(path_type=Path),
    default=None,
    show_default=True,
    help="Parent of the dataset statistics directories",
)
@click.option(
    "--output-dir",
    "output_root",
    type=click.Path(path_type=Path),
    default=ROOT,
    show_default=True,
    help="Run root containing stats, plots, and tables",
)
def main(
    variant: str,
    tiebreak: str,
    n_cand_list: Sequence[int] = list(range(6, 10)),
    *,
    stats_root: Path | None = None,
    output_root: Path = ROOT,
) -> None:
    """Save Scottish metric boxplots and export aggregate statistics for the selected labels.

    Args:
        variant (str): Metric variant to plot (e.g., average or worst_case).
        tiebreak (str): Tiebreak rule to plot (e.g., lex or random).
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

    stat_file_base_dir = str((stats_root / "scottish_stats").resolve())
    output_dir = str(output_root / "plots/scottish")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_plot_name = f"{str(output_dir)}/scottish_sigma_plots_{variant}_{tiebreak}.png"

    # ==========================
    # Make the scottish boxplots
    # ==========================

    outputs_by_election_type = load_outputs_by_election_type(
        stats_root / "scottish_stats", ordered_rules, variants=(variant,), tiebreaks=(tiebreak,)
    )

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

    _, ax = plt.subplots(len(metric_label_pairs), 1, figsize=(20, 6 * len(metric_label_pairs)))
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
    export_aggregate_tables(
        stat_file_base_dir, ordered_rules, n_cand_list, variant, tiebreak, output_root=output_root
    )


if __name__ == "__main__":
    main()
