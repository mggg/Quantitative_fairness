"""Plot raw BT score distributions pooled by alpha tuple and total candidate count."""

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple, Sequence

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.pool_alpha_metrics import AlphaScoreGroup, grouped_scores_path
from voting_metrics_main_code.constants import (
    BT_ALPHA_COMBINATIONS,
    BT_CANDIDATE_COMBINATIONS,
    COMPARISON_RULE_ORDER,
    MetricVariant,
)
from voting_metrics_main_code.replication import ROOT


def load_alpha_samples(
    metric_base_name: str,
    alpha: tuple[float, float, float, float],
    ordered_rules: Sequence[str],
    ordered_n_cands: Sequence[int],
    grouped_stats_root: Path,
    n_seats: int,
    variant: str,
    tiebreak: str,
    interpolation_type: str,
) -> dict[str, dict[int, list[float]]]:
    """Load pooled raw scores for one full alpha tuple, in rule and candidate-count order.

    Args:
        metric_base_name (str): Metric identifier.
        alpha (tuple[float, float, float, float]): Four Dirichlet parameters in experiment order.
        ordered_rules (Sequence[str]): Voting rules in display order.
        ordered_n_cands (Sequence[int]): Total candidate counts in display order.
        grouped_stats_root (Path): Exact directory produced by pool_alpha_metrics.py.
        n_seats (int): Number of elected seats.
        variant (str): Metric aggregation variant.
        tiebreak (str): Tie-breaking method.
        interpolation_type (str): UM interpolation or 'None' for IIA.

    Returns:
        dict[str, dict[int, list[float]]]: Raw scores keyed by rule and total candidate count.

    Raises:
        FileNotFoundError: Pooled scores have not been generated for this selection.
        ValueError: A requested group is missing, duplicated, or empty.
    """
    path = grouped_scores_path(
        grouped_stats_root, metric_base_name, variant, interpolation_type, n_seats, tiebreak
    )
    with path.open() as source:
        groups: list[AlphaScoreGroup] = json.load(source)

    samples: dict[str, dict[int, list[float]]] = {rule: {} for rule in ordered_rules}
    for group in groups:
        if tuple(group["alpha"]) != alpha or group["rule"] not in samples:
            continue

        rule, n_cands = group["rule"], group["n_cands"]
        if n_cands in samples[rule] or not group["scores"]:
            raise ValueError(
                f"Duplicate or empty alpha group in {path}: {alpha}, {rule}, {n_cands}"
            )
        samples[rule][n_cands] = group["scores"]

    for rule in ordered_rules:
        if any(n_cands not in samples[rule] for n_cands in ordered_n_cands):
            raise ValueError(f"Missing alpha group in {path}: {alpha}, {rule}")

    return samples


def build_plot_for_metric_and_alpha(
    metric_base_name: str,
    alpha: tuple[float, float, float, float],
    ordered_rules: Sequence[str],
    ordered_n_cands: Sequence[int],
    rule_color_map: Mapping[str, str | tuple[float, float, float]],
    ax: Axes,
    y_label: str,
    grouped_stats_root: Path,
    n_seats: int,
    variant: str,
    tiebreak: str,
    interpolation_type: str,
) -> None:
    """Draw one metric-and-alpha boxplot panel across candidate counts and voting rules.

    Args:
        metric_base_name (str): Metric identifier used in the statistics directory and filenames.
        alpha (tuple[float, float, float, float]): Dirichlet parameters in experiment order.
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        ordered_n_cands (Sequence[int]): Candidate counts in display order.
        rule_color_map (Mapping[str, str | tuple[float, float, float]]): Mapping from voting rule
            names to color strings or RGB tuples.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str): Label for the y-axis.
        grouped_stats_root (Path): Exact directory produced by pool_alpha_metrics.py.
        n_seats (int): Number of seats to elect.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
    """
    ordered_outputs = load_alpha_samples(
        metric_base_name,
        alpha,
        ordered_rules,
        ordered_n_cands,
        grouped_stats_root,
        n_seats,
        variant,
        tiebreak,
        interpolation_type,
    )

    df_list = []

    for n_cands in ordered_n_cands:
        df_data = [ordered_outputs[rule][n_cands] for rule in ordered_rules]
        df = pd.DataFrame(df_data, index=list(ordered_outputs)).T
        df = df.melt(var_name="rule", value_name="value")
        df["n_cands"] = n_cands

        df_list.append(df)

    long = pd.concat(df_list, ignore_index=True)

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=False,
        fliersize=1,
        # Seaborn accepts percentile pairs; its stub only declares a float.
        whis=[1, 99],  # type: ignore[arg-type]
    )

    ax.set_xlabel("Total candidates")
    ax.set_ylabel(f"{y_label}\n{variant.replace('_', ' ')}")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"$\\alpha$={alpha}\n{n_seats} seats", fontsize=12)


class MetricPanel(NamedTuple):
    """A metric selection and its display label for one row of alpha plots."""

    metric: str
    variant: MetricVariant
    interpolation: str
    label: str


def iia_comparison_panels(ranking_variant: MetricVariant) -> list[MetricPanel]:
    """Select worst-case UM and IIA comparisons, varying only the ranking IIA aggregation.

    Args:
        ranking_variant (MetricVariant): Aggregation for ranking IIA; other IIA rows use average.

    Returns:
        list[MetricPanel]: Four metric rows in display order.
    """
    return [
        MetricPanel("sigma_UM", "worst_case", "asin", "$\\sigma_{UM}$ ranking ASIN"),
        MetricPanel(
            "sigma_UM_winner_set", "worst_case", "asin", "$\\sigma_{UM}$ winner-set ranking ASIN"
        ),
        MetricPanel("sigma_IIA", ranking_variant, "None", "$\\sigma_{IIA}$ ranking"),
        MetricPanel("sigma_IIA_winner_set", "average", "None", "$\\sigma_{IIA}$ winner-set"),
    ]


def variant_comparison_panels(variant: MetricVariant) -> list[MetricPanel]:
    """Select all metric and interpolation comparisons for a single aggregation variant.

    Args:
        variant (MetricVariant): Aggregation applied to every metric row.

    Returns:
        list[MetricPanel]: Six metric rows in display order.
    """
    return [
        MetricPanel("sigma_UM", variant, "odds", "$\\sigma_{UM}$ ranking ODDS"),
        MetricPanel("sigma_UM", variant, "asin", "$\\sigma_{UM}$ ranking ASIN"),
        MetricPanel(
            "sigma_UM_winner_set", variant, "odds", "$\\sigma_{UM}$ winner-set ranking ODDS"
        ),
        MetricPanel(
            "sigma_UM_winner_set", variant, "asin", "$\\sigma_{UM}$ winner-set ranking ASIN"
        ),
        MetricPanel("sigma_IIA", variant, "None", "$\\sigma_{IIA}$ ranking"),
        MetricPanel("sigma_IIA_winner_set", variant, "None", "$\\sigma_{IIA}$ winner-set"),
    ]


def save_metric_grid(
    panels: Sequence[MetricPanel],
    n_seats: int,
    tiebreak: str,
    output_file: Path,
    *,
    stats_root: Path,
) -> None:
    """Load and save metric rows across the configured alpha tuples with a shared voting-rule legend.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
        panels (Sequence[MetricPanel]): Metric rows in display order.
        n_seats (int): Seat count encoded in the input paths.
        tiebreak (str): Tiebreak token used to select statistics.
        output_file (Path): Destination image path.
    """
    alpha_values = BT_ALPHA_COMBINATIONS
    candidate_counts = sorted({sum(split) for split in BT_CANDIDATE_COMBINATIONS})
    rules = COMPARISON_RULE_ORDER
    statistics_dir = stats_root / "bt_alpha_grouped"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
    figure, axes = plt.subplots(
        len(panels),
        len(alpha_values),
        squeeze=False,
        figsize=(5 * len(alpha_values), 4 * len(panels)),
        dpi=300,
        layout="constrained",
    )
    palette = dict(zip(rules, sns.color_palette("colorblind", len(rules))))

    for alpha_index, alpha in enumerate(alpha_values):
        for row, panel in enumerate(panels):
            build_plot_for_metric_and_alpha(
                panel.metric,
                alpha,
                rules,
                candidate_counts,
                palette,
                axes[row, alpha_index],
                y_label=panel.label,
                grouped_stats_root=statistics_dir,
                n_seats=n_seats,
                variant=panel.variant,
                tiebreak=tiebreak,
                interpolation_type=panel.interpolation,
            )

    figure.legend(
        handles=[Patch(facecolor=palette[rule], label=rule) for rule in rules],
        title="Voting Rule",
        loc="outside right center",
        frameon=True,
        fontsize="large",
        title_fontsize="large",
    )

    plt.savefig(output_file, bbox_inches="tight", dpi=300)
    plt.close(figure)


def plot_average_iia_panel(
    n_seats: int, tiebreak: str, *, stats_root: Path, output_root: Path
) -> None:
    """Save a panel grid comparing worst-case ASIN UM with average IIA across alpha values.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
        output_root (Path): Run root containing stats, plots, and tables.
        n_seats (int): Number of seats to elect.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        output_root
        / "plots"
        / "bt_plots"
        / "alpha_boxplots"
        / (f"um_worst_case_iia_average__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(
        iia_comparison_panels("average"), n_seats, tiebreak, output_file, stats_root=stats_root
    )


def plot_worst_case_ranking_iia_panel(
    n_seats: int, tiebreak: str, *, stats_root: Path, output_root: Path
) -> None:
    """Save the alpha panel grid with worst-case ranking IIA and average winner-set IIA.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
        output_root (Path): Run root containing stats, plots, and tables.
        n_seats (int): Number of seats to elect.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        output_root
        / "plots"
        / "bt_plots"
        / "alpha_boxplots"
        / (f"um_worst_case_iia_ranking_worst_case__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(
        iia_comparison_panels("worst_case"), n_seats, tiebreak, output_file, stats_root=stats_root
    )


def plot_variant_comparison(
    n_seats: int,
    variant: MetricVariant,
    tiebreak: str,
    *,
    stats_root: Path,
    output_root: Path,
) -> None:
    """Save an alpha panel grid comparing UM interpolations and IIA metric families.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
        output_root (Path): Run root containing stats, plots, and tables.
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        output_root
        / "plots"
        / "bt_plots"
        / "alpha_boxplots"
        / (f"metric_comparison__NSEATS_{n_seats}__VARIANT_{variant}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(
        variant_comparison_panels(variant), n_seats, tiebreak, output_file, stats_root=stats_root
    )


def plot_individual_metrics(
    n_seats: int,
    variant: MetricVariant,
    tiebreak: str,
    *,
    stats_root: Path,
    output_root: Path,
) -> None:
    """Save a separate alpha panel grid for each metric and interpolation.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
        output_root (Path): Run root containing stats, plots, and tables.
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    for panel in variant_comparison_panels(variant):
        output_file = (
            output_root
            / "plots"
            / "bt_plots"
            / "alpha_boxplots"
            / (
                f"METRIC_{panel.metric}__NSEATS_{n_seats}__VARIANT_{variant}"
                f"__TIEBREAK_{tiebreak}__INTERP_{panel.interpolation}.png"
            )
        )
        save_metric_grid([panel], n_seats, tiebreak, output_file, stats_root=stats_root)


@click.command()
@click.option("--n-seats", type=int, default=3, show_default=True, help="Number of seats")
@click.option(
    "--variant",
    type=click.Choice(["worst_case", "average"]),
    default="worst_case",
    show_default=True,
)
@click.option("--tiebreak", type=click.Choice(["lex", "random"]), default="lex", show_default=True)
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
    n_seats: int,
    variant: MetricVariant,
    tiebreak: str,
    *,
    stats_root: Path | None = None,
    output_root: Path = ROOT,
) -> None:
    """Save combined and individual metric boxplot grids from pooled two-bloc BT scores.

    Args:
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()
    print(f"Statistics: {stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")
    print("Subset IIA is excluded: no saved two-bloc scores are available for that metric.")

    plot_average_iia_panel(n_seats, tiebreak, stats_root=stats_root, output_root=output_root)
    plot_worst_case_ranking_iia_panel(
        n_seats, tiebreak, stats_root=stats_root, output_root=output_root
    )
    plot_variant_comparison(
        n_seats, variant, tiebreak, stats_root=stats_root, output_root=output_root
    )
    plot_individual_metrics(
        n_seats, variant, tiebreak, stats_root=stats_root, output_root=output_root
    )


if __name__ == "__main__":
    main()
