"""Create scatter plots comparing UM and IIA metrics in Scottish data."""

from glob import glob
from itertools import product
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence
from itertools import product

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import seaborn as sns

import sys
sys.path.append(str(Path(__file__).resolve().parent))

from create_scottish_scatterplots import (
    load_outputs_by_election_type, 
    get_limited_metric_key_pairs, 
    rule_color_map, 
    collect_scatter_points,
    draw_limited_scatter_base,
)

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

    Returns:
        Path: Full output file path.
    """
    percentile_suffix = f"{int(percentile*100)}th_percentile" if percentile is not None else "mean"
    return line_dir / (
        f"{percentile_suffix}_line_"
        f"{um_key.removesuffix(f'_{variant_um}_asin_{tiebreak}')}_vs_"
        f"{iia_key.removesuffix(f'_{variant_iia}_{tiebreak}')}_"
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
    x_data, y_data = collect_scatter_points(
        outputs_by_election_type=outputs_by_election_type,
        voting_rule=voting_rule,
        um_key=um_key,
        iia_key=iia_key,
    )
    if percentile is not None:
        threshold_x = pd.Series(x_data).quantile(1 - percentile)
        threshold_y = pd.Series(y_data).quantile(percentile)
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
    return ax



def run_limited_line_plots(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    ordered_rules: Sequence[str],
    output_dir: Path,
    variant_um: str = "worst_case",
    variant_iia: str = "average",
    tiebreak: str = "lex",
    lineplot_subdir:str = "lineplot_by_voting_rule",
    overlay_fn: (
        Callable[[Axes, str, str, str, list[float], list[float]], None] | None
    ) = None,
) -> None:
    """Generate the limited Scottish line plots for all rules.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        ordered_rules (Sequence[str]): Rules to include.
        output_dir (Path): Base plot output directory.
        variant_um (str): UM metric variant.
        variant_iia (str): IIA metric variant.
        tiebreak (str): Tiebreak suffix used in metric keys.
        lineplot_subdir (str): Subdirectory name under ``output_dir``.
        overlay_fn (Callable[[Axes, str, str, str, list[float], list[float]], None] | None):
            Optional overlay callback for each plot.
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
        ax.vlines(
            0.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
        )
        ax.vlines(
            1.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
        )
        ax.hlines(
            0.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
        )
        ax.hlines(
            1.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
        )
        plt.savefig(plot_name, bbox_inches="tight", dpi=300)
        plt.close(fig)

def main() -> None:
    """Run the Scottish limited scatterplot pipeline."""
    ordered_rules = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]
    top_dir = Path(__file__).resolve().parents[2]
    stats_dir = top_dir / "stats" / "scottish_stats"
    output_dir = top_dir / "plots" / "scottish"
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
