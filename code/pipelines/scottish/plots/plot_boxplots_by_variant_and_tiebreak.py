"""Create Scottish boxplots split by variant and tiebreak."""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import click
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.axes import Axes

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.scottish.plots._data import (
    build_boxplot_table,
    export_aggregate_tables,
    load_outputs_by_election_type,
)
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
    metric_values_df = build_boxplot_table(ordered_outputs, n_cand_list, metric, borda_only=use_one)

    sns.boxplot(
        data=metric_values_df,
        x="n_cands",
        y="value",
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=not use_one,
        # Seaborn accepts percentile pairs; its stub only declares a float.
        whis=[1, 99],  # type: ignore[arg-type]
    )

    ax.set_ylabel(y_label, fontsize=16)
    ax.set_ylim(-0.1, 1.1)

    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


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
    n_cand_list: Sequence[int] = range(6, 10),
    *,
    stats_root: Path | None = None,
    output_root: Path = ROOT,
) -> None:
    """Save Scottish metric boxplots and export aggregate statistics for the selected labels.

    Args:
        variant (str): Metric variant to plot (e.g., average or worst_case).
        tiebreak (str): Tiebreak rule to plot (e.g., lex or random).
        n_cand_list (Sequence[int], optional): Candidate counts to include. Defaults to
            range(6, 10).
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root. Defaults to None.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()

    ordered_rules = RULE_ORDER

    stat_file_base_dir = stats_root / "scottish_stats"
    output_dir = output_root / "plots/scottish"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_plot_name = output_dir / f"scottish_sigma_plots_{variant}_{tiebreak}.png"

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
