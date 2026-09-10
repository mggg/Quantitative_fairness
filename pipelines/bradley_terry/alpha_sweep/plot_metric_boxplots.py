"""Plot metric boxplots by alpha and candidate count from historical BT statistics."""

import json
import sys
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple, Sequence

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import NON_RANDOM_RULE_ORDER, MetricVariant
from voting_metrics_main_code.replication import PLOTS_DIR, STATS_INPUT


def load_file(file_path: str | Path) -> list[float]:
    """Load a metric JSON array, printing an error and returning an empty list on failure.

    Args:
        file_path (str | Path): Path to a JSON array of metric scores.

    Returns:
        list[float]: Loaded scores, or an empty list if opening or decoding the file fails.
    """
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")

    return []


def create_ordered_dict_for_metric_and_alpha(
    metric_base_name: str,
    alpha: float,
    ordered_rules: Sequence[str],
    ordered_n_cands: Sequence[int],
    stat_file_base_dir: str,
    n_seats: int,
    variant: str,
    tiebreak: str,
    interpolation_type: str,
) -> dict[str, dict[int, list[float]]]:
    """Load scores for one metric and alpha, preserving rule and candidate-count order.

    Args:
        metric_base_name (str): Metric identifier used in the statistics directory and filenames.
        alpha (float): Dirichlet concentration parameter shared by the candidates.
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        ordered_n_cands (Sequence[int]): Candidate counts in display order.
        stat_file_base_dir (str): Base directory containing the metric JSON files.
        n_seats (int): Number of seats to elect.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.

    Returns:
        dict[str, dict[int, list[float]]]: Scores keyed by rule and candidate count. Failed file
            loads contribute empty lists.
    """
    return {
        rule: {
            n_cands: load_file(
                str(
                    Path(
                        f"{stat_file_base_dir}/{metric_base_name}/{n_cands:02d}"
                        f"/alpha_{alpha:.2f}/METRIC_{metric_base_name}__SEATS_{n_seats}"
                        f"__NCANDS_{n_cands}__ALPHA_{alpha:.2f}__TYPE_{rule}"
                        f"__VARIANT_{variant}__TIEBREAK_{tiebreak}"
                        f"__INTERP_{interpolation_type}.json"
                    ).resolve()
                )
            )
            for n_cands in ordered_n_cands
        }
        for rule in ordered_rules
    }


def build_plot_for_metric_and_alpha(
    metric_base_name: str,
    alpha: float,
    ordered_rules: Sequence[str],
    ordered_n_cands: Sequence[int],
    rule_color_map: Mapping[str, str | tuple[float, float, float]],
    ax: Axes,
    y_label: str,
    stat_file_base_dir: str,
    n_seats: int,
    variant: str,
    tiebreak: str,
    interpolation_type: str,
) -> None:
    """Draw one metric-and-alpha boxplot panel across candidate counts and voting rules.

    Args:
        metric_base_name (str): Metric identifier used in the statistics directory and filenames.
        alpha (float): Dirichlet concentration parameter shared by the candidates.
        ordered_rules (Sequence[str]): Voting rules in the order to load or display.
        ordered_n_cands (Sequence[int]): Candidate counts in display order.
        rule_color_map (Mapping[str, str | tuple[float, float, float]]): Mapping from voting rule
            names to color strings or RGB tuples.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str): Label for the y-axis.
        stat_file_base_dir (str): Base directory containing the metric JSON files.
        n_seats (int): Number of seats to elect.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
    """
    ordered_outputs = create_ordered_dict_for_metric_and_alpha(
        metric_base_name,
        alpha,
        ordered_rules,
        ordered_n_cands,
        stat_file_base_dir,
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

    ax.set_ylabel(y_label)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(
        f"Metric: {y_label}, $\\alpha$={Fraction(alpha).limit_denominator()} Seats: {n_seats}"
    )


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
        list[MetricPanel]: Five metric rows in display order.
    """
    return [
        MetricPanel("sigma_UM", "worst_case", "asin", "$\\sigma_{UM}$ ranking ASIN"),
        MetricPanel(
            "sigma_UM_winner_set", "worst_case", "asin", "$\\sigma_{UM}$ winner-set ranking ASIN"
        ),
        MetricPanel("sigma_IIA", ranking_variant, "None", "$\\sigma_{IIA}$ ranking"),
        MetricPanel("sigma_IIA_all_subset", "average", "None", "$\\sigma_{IIA}$ subset"),
        MetricPanel("sigma_IIA_winner_set", "average", "None", "$\\sigma_{IIA}$ winner-set"),
    ]


def variant_comparison_panels(variant: MetricVariant) -> list[MetricPanel]:
    """Select all metric and interpolation comparisons for a single aggregation variant.

    Args:
        variant (MetricVariant): Aggregation applied to every metric row.

    Returns:
        list[MetricPanel]: Seven metric rows in display order.
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
        MetricPanel("sigma_IIA_all_subset", variant, "None", "$\\sigma_{IIA}$ subset"),
        MetricPanel("sigma_IIA_winner_set", variant, "None", "$\\sigma_{IIA}$ winner-set"),
    ]


def save_metric_grid(
    panels: Sequence[MetricPanel], n_seats: int, tiebreak: str, output_file: Path
) -> None:
    """Load and save metric rows across the five alpha values with a shared voting-rule legend.

    Args:
        panels (Sequence[MetricPanel]): Metric rows in display order.
        n_seats (int): Seat count encoded in the input paths.
        tiebreak (str): Tiebreak token used to select statistics.
        output_file (Path): Destination image path.
    """
    alpha_values = (1 / 3, 1 / 2, 1, 2, 3)
    candidate_counts = range(6, 10)
    rules = NON_RANDOM_RULE_ORDER
    statistics_dir = str((STATS_INPUT / "bt_profile_stats" / f"{n_seats}_seats").resolve())
    output_file.parent.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(
        len(panels),
        len(alpha_values),
        squeeze=False,
        figsize=(7 * len(alpha_values), 5 * len(panels)),
        dpi=300,
        gridspec_kw={"hspace": 0.3},
    )
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
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
                stat_file_base_dir=statistics_dir,
                n_seats=n_seats,
                variant=panel.variant,
                tiebreak=tiebreak,
                interpolation_type=panel.interpolation,
            )

    figure.legend(
        handles=[Patch(facecolor=palette[rule], label=rule) for rule in rules],
        title="Voting Rule",
        loc="center left",
        bbox_to_anchor=(0.93, 0.5),
        frameon=True,
        fontsize="large",
        title_fontsize="large",
    )

    plt.savefig(output_file, bbox_inches="tight", dpi=300)
    plt.close(figure)


def plot_average_iia_panel(n_seats: int, tiebreak: str) -> None:
    """Save a panel grid comparing worst-case ASIN UM with average IIA across alpha values.

    Args:
        n_seats (int): Number of seats to elect.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        PLOTS_DIR / "simulated_BT_plots" / (f"BESTMERGE__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(iia_comparison_panels("average"), n_seats, tiebreak, output_file)


def plot_worst_case_ranking_iia_panel(n_seats: int, tiebreak: str) -> None:
    """Save the alpha panel grid with worst-case ranking IIA and average subset/winner-set IIA.

    Args:
        n_seats (int): Number of seats to elect.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        PLOTS_DIR / "simulated_BT_plots" / (f"ALTMERGE__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(iia_comparison_panels("worst_case"), n_seats, tiebreak, output_file)


def plot_variant_comparison(n_seats: int, variant: MetricVariant, tiebreak: str) -> None:
    """Save an alpha panel grid comparing UM interpolations and IIA metric families.

    Args:
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    output_file = (
        PLOTS_DIR
        / "simulated_BT_plots"
        / (f"AGGREGATE__NSEATS_{n_seats}__VARIANT_{variant}__TIEBREAK_{tiebreak}.png")
    )
    save_metric_grid(variant_comparison_panels(variant), n_seats, tiebreak, output_file)


def plot_individual_metrics(n_seats: int, variant: MetricVariant, tiebreak: str) -> None:
    """Save a separate alpha panel grid for each metric and interpolation.

    Args:
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)

    for panel in variant_comparison_panels(variant):
        output_file = (
            PLOTS_DIR
            / "simulated_BT_plots"
            / (
                f"METRIC_{panel.metric}__NSEATS_{n_seats}__VARIANT_{variant}"
                f"__TIEBREAK_{tiebreak}__INTERP_{panel.interpolation}.png"
            )
        )
        save_metric_grid([panel], n_seats, tiebreak, output_file)


@click.command()
@click.option("--n-seats", type=int, default=1, help="Number of seats")
@click.option("--variant", type=click.Choice(["worst_case", "average"]))
@click.option("--tiebreak", type=click.Choice(["lex", "random"]))
def main(n_seats: int, variant: MetricVariant, tiebreak: str) -> None:
    """Save combined and individual metric boxplot grids across the single-alpha profile sweep.

    Args:
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Metric aggregation variant, 'average' or 'worst_case'.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
    """
    plot_average_iia_panel(n_seats, tiebreak)
    plot_worst_case_ranking_iia_panel(n_seats, tiebreak)
    plot_variant_comparison(n_seats, variant, tiebreak)
    plot_individual_metrics(n_seats, variant, tiebreak)


if __name__ == "__main__":
    main()
