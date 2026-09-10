"""Plot UM and IIA percentile thresholds and means by Scottish voting rule."""

import sys
from itertools import product
from pathlib import Path
from typing import Callable, Mapping, Sequence

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.scottish.plots._data import load_outputs_by_election_type
from pipelines.scottish.plots.plot_um_iia_scatter import (
    collect_scatter_points,
    get_limited_metric_key_pairs,
    rule_color_map,
)

from voting_metrics_main_code.replication import PLOTS_DIR, STATS_INPUT

rule_to_dot_size = {
    "borda": 9,
    "3-approval": 9.1,
    "2-approval": 9.2,
    "plurality": 9.3,
    "stv": 9.4,
    "ranked-pairs": 9.5,
    "random": 9.6,
}


def build_limited_line_plot_name(
    line_dir: Path,
    um_key: str,
    iia_key: str,
    variant_um: str,
    variant_iia: str,
    tiebreak: str,
    percentile: float | None = None,
) -> Path:
    """Build output filename for one limited line plot.

    Args:
        line_dir (Path): Output plot directory.
        um_key (str): UM metric key.
        iia_key (str): IIA metric key.
        variant_um (str): UM variant string used in key suffix.
        variant_iia (str): IIA variant string used in key suffix.
        tiebreak (str): Tiebreak string used in key suffix.
        percentile (float | None, optional): Upper-tail probability encoded in the filename; None
            selects the mean filename. Defaults to None.

    Returns:
        Path: Full output file path.
    """
    percentile_suffix = (
        f"{int(percentile * 100)}th_percentile" if percentile is not None else "mean"
    )
    key_to_title = {
        "sigma_UM": "rho_UM",
        "sigma_IIA": "rho_IIA",
        "sigma_UM_winner_set": "sigma_UM",
        "sigma_IIA_winner_set": "sigma_IIA",
    }

    return line_dir / (
        f"{percentile_suffix}_line_"
        f"{key_to_title[um_key.removesuffix(f'_{variant_um}_asin_{tiebreak}')]}_vs_"
        f"{key_to_title[iia_key.removesuffix(f'_{variant_iia}_{tiebreak}')]}_"
        "all_voting_rules.png"
    )


def add_percentile_lines(
    ax: Axes,
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    voting_rule: str,
    um_key: str,
    iia_key: str,
    percentile: float | None,
) -> Axes:
    """Draw horizontal and vertical metric thresholds and mark their intersection.

    Args:
        ax (Axes): Matplotlib axes to draw into.
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Metric
            score lists keyed by rule, candidate-count string, and metric key.
        voting_rule (str): Voting rule name used to select statistics.
        um_key (str): UM metric key for x-axis values.
        iia_key (str): IIA metric key for y-axis values.
        percentile (float | None): Upper-tail probability; use quantile 1 - percentile, or means
            when None.

    Returns:
        Axes: Input axes with the rule-colored threshold lines and intersection marker.

    Raises:
        ValueError: A supplied percentile is outside [0, 1].
    """
    x_data, y_data = collect_scatter_points(
        outputs_by_election_type=outputs_by_election_type,
        voting_rule=voting_rule,
        um_key=um_key,
        iia_key=iia_key,
    )

    if percentile is not None:
        threshold_x = pd.Series(x_data).quantile(1 - percentile)
        threshold_y = pd.Series(y_data).quantile(1 - percentile)
    else:
        threshold_x = pd.Series(x_data).mean()
        threshold_y = pd.Series(y_data).mean()

    ax.axvline(
        threshold_x,
        color=rule_color_map[voting_rule],
        linestyle="-",
        linewidth=3,
        zorder=-1,
        alpha=1.0,
    )
    ax.axhline(
        threshold_y,
        color=rule_color_map[voting_rule],
        linestyle="-",
        linewidth=3,
        zorder=-1,
        alpha=1.0,
    )
    ax.plot(
        threshold_x,
        threshold_y,
        marker="o",
        color=rule_color_map[voting_rule],
        markersize=rule_to_dot_size[voting_rule],
        zorder=3,
    )

    return ax


def run_limited_line_plots(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    ordered_rules: Sequence[str],
    output_dir: Path,
    variant_um: str = "worst_case",
    variant_iia: str = "average",
    tiebreak: str = "lex",
    lineplot_subdir: str = "lineplot_by_voting_rule",
    overlay_fn: (Callable[[Axes, str, str, str, list[float], list[float]], None] | None) = None,
) -> None:
    """Generate the limited Scottish line plots for all rules.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Nested
            metric values by rule and candidate count.
        ordered_rules (Sequence[str]): Rules to include.
        output_dir (Path): Base plot output directory.
        variant_um (str, optional): UM metric variant. Defaults to 'worst_case'.
        variant_iia (str, optional): IIA metric variant. Defaults to 'average'.
        tiebreak (str, optional): Tiebreak suffix used in metric keys. Defaults to 'lex'.
        lineplot_subdir (str, optional): Subdirectory name under ``output_dir``. Defaults to
            'lineplot_by_voting_rule'.
        overlay_fn (Callable[[Axes, str, str, str, list[float], list[float]], None] | None, optional):
            Optional overlay callback for each plot. Defaults to None.
    """
    lineplot_dir = output_dir / lineplot_subdir
    lineplot_dir.mkdir(parents=True, exist_ok=True)
    metric_pairs = get_limited_metric_key_pairs(
        variant_um=variant_um,
        variant_iia=variant_iia,
        tiebreak=tiebreak,
    )
    percentiles = [0.50, 0.95, 1.00, None]

    for (um_key, iia_key), percentile in product(metric_pairs, percentiles):
        sns.set_theme(style="ticks", context="notebook", font="serif", font_scale=1.2)
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))

        plot_name = build_limited_line_plot_name(
            line_dir=lineplot_dir,
            um_key=um_key,
            iia_key=iia_key,
            variant_um=variant_um,
            variant_iia=variant_iia,
            tiebreak=tiebreak,
            percentile=percentile,
        )

        for voting_rule in ordered_rules:
            add_percentile_lines(
                ax=ax,
                outputs_by_election_type=outputs_by_election_type,
                voting_rule=voting_rule,
                um_key=um_key,
                iia_key=iia_key,
                percentile=percentile,
            )

        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)

        for draw_line in (ax.vlines, ax.hlines):
            for boundary in (0.0, 1.0):
                draw_line(
                    boundary,
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


def main() -> None:
    """Plot Scottish UM and IIA percentile thresholds and means."""
    ordered_rules = [
        "3-approval",
        "borda",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]
    stats_dir = STATS_INPUT / "scottish_stats"
    output_dir = PLOTS_DIR / "scottish"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs_by_election_type = load_outputs_by_election_type(
        stats_dir=stats_dir,
        ordered_rules=ordered_rules,
    )
    run_limited_line_plots(
        outputs_by_election_type=outputs_by_election_type,
        ordered_rules=ordered_rules,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
