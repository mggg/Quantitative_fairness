"""Create limited Scottish scatterplots with bootstrap rectangles and means."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.append(str(Path(__file__).resolve().parents[2]))

from pipelines.scottish.create_scottish_scatterplots import (
    build_limited_scatter_plot_name,
    draw_limited_scatter_base,
    get_limited_metric_key_pairs,
    load_outputs_by_election_type,
    rule_color_map,
    run_limited_scatter_plots,
)


def _metric_name_from_key(metric_key: str, tiebreak: str) -> str:
    """Strip tiebreak suffix from a metric key."""
    suffix = f"_{tiebreak}"
    if not metric_key.endswith(suffix):
        raise ValueError(
            f"Metric key {metric_key!r} does not end with suffix {suffix!r}."
        )
    return metric_key.removesuffix(suffix)


def load_rectangle_lookup(
    bootstrap_dir: Path,
    metric_pairs: list[tuple[str, str]],
    tiebreak: str,
) -> dict[tuple[str, str, str, int | None], tuple[float, float, float, float]]:
    """Load rectangle bounds keyed by rule + metric keys + candidate size.

    Args:
        bootstrap_dir (Path): Directory containing bootstrap rectangle CSV files.
        metric_pairs (list[tuple[str, str]]): List of ``(um_key, iia_key)`` pairs.
        tiebreak (str): Tiebreak value to filter rows.

    Returns:
        dict[tuple[str, str, str, int | None], tuple[float, float, float, float]]:
            Mapping from ``(rule, um_key, iia_key, candidate_size)`` to
            ``(um_L, um_U, iia_L, iia_U)``. Pooled rows use ``candidate_size=None``.
    """
    lookup: dict[
        tuple[str, str, str, int | None], tuple[float, float, float, float]
    ] = {}

    for um_key, iia_key in metric_pairs:
        metric_um = _metric_name_from_key(um_key, tiebreak=tiebreak)
        metric_iia = _metric_name_from_key(iia_key, tiebreak=tiebreak)
        rectangle_csv = (
            bootstrap_dir / f"bootstrap_rectangles_{metric_iia}_vs_{metric_um}.csv"
        )
        if not rectangle_csv.exists():
            print(f"Missing rectangle file, skipping: {rectangle_csv}")
            continue

        df = pd.read_csv(rectangle_csv)
        filtered = df[df["tiebreak"] == tiebreak]
        for _, row in filtered.iterrows():
            candidate_size = None
            if not pd.isna(row["candidate_size"]):
                candidate_size = int(row["candidate_size"])
            lookup[(row["rule"], um_key, iia_key, candidate_size)] = (
                float(row["um_L"]),
                float(row["um_U"]),
                float(row["iia_L"]),
                float(row["iia_U"]),
            )

    return lookup


def make_bootstrap_overlay(
    rectangle_lookup: dict[
        tuple[str, str, str, int | None], tuple[float, float, float, float]
    ],
    candidate_size: int | None = None,
) -> Callable[[Axes, str, str, str, list[float], list[float]], None]:
    """Create an overlay callback that draws pooled rectangles and means."""

    def _zoom_limits(
        values: list[float],
        lower_hint: float | None = None,
        upper_hint: float | None = None,
        min_span: float = 0.08,
        pad_fraction: float = 0.08,
    ) -> tuple[float, float]:
        """Compute a zoomed axis range around observed values + rectangle hints."""
        arr = np.asarray(values, dtype=float)
        low = float(arr.min())
        high = float(arr.max())
        if lower_hint is not None:
            low = min(low, lower_hint)
        if upper_hint is not None:
            high = max(high, upper_hint)

        span = high - low
        if span < min_span:
            center = 0.5 * (low + high)
            half = 0.5 * min_span
            low = center - half
            high = center + half

        pad = pad_fraction * (high - low)
        low -= pad
        high += pad
        return max(-0.05, low), min(1.05, high)

    def overlay(
        ax: Axes,
        voting_rule: str,
        um_key: str,
        iia_key: str,
        x_data: list[float],
        y_data: list[float],
    ) -> None:
        key = (voting_rule, um_key, iia_key, candidate_size)
        rectangle = rectangle_lookup.get(key)
        um_l = um_u = iia_l = iia_u = None
        if rectangle is not None:
            um_l, um_u, iia_l, iia_u = rectangle
            ax.add_patch(
                plt.Rectangle(
                    (um_l, iia_l),
                    um_u - um_l,
                    iia_u - iia_l,
                    fill=False,
                    linewidth=1.5,
                    edgecolor="black",
                    zorder=3,
                )
            )

        mean_x = float(np.mean(x_data))
        mean_y = float(np.mean(y_data))
        ax.scatter([mean_x], [mean_y], color="black", s=5, zorder=4)

        x_min, x_max = _zoom_limits(x_data, lower_hint=um_l, upper_hint=um_u)
        y_min, y_max = _zoom_limits(y_data, lower_hint=iia_l, upper_hint=iia_u)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

    return overlay


def run_limited_scatter_plots_by_candidate_count_with_bootstrap(
    outputs_by_election_type: dict[str, dict[str, dict[str, list[float]]]],
    ordered_rules: Sequence[str],
    output_dir: Path,
    metric_pairs: list[tuple[str, str]],
    variant_um: str,
    variant_iia: str,
    tiebreak: str,
    rectangle_lookup: dict[
        tuple[str, str, str, int | None], tuple[float, float, float, float]
    ],
) -> None:
    """Create per-candidate-count limited bootstrap scatterplots.

    Args:
        outputs_by_election_type (dict[str, dict[str, dict[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        ordered_rules (Sequence[str]): Rules to include.
        output_dir (Path): Base output directory.
        metric_pairs (list[tuple[str, str]]): Limited metric key pairs as
            ``(um_key, iia_key)``.
        variant_um (str): UM variant suffix used for filenames.
        variant_iia (str): IIA variant suffix used for filenames.
        tiebreak (str): Tiebreak suffix used in metric keys.
        rectangle_lookup (dict[tuple[str, str, str, int | None], tuple[float, float, float, float]]):
            Rectangle lookup keyed by ``(rule, um_key, iia_key, candidate_size)``.
    """
    base_dir = output_dir / "scatter_by_voting_rule_with_bootstrap"
    sns.set_theme(style="ticks", context="notebook", font="serif", font_scale=1.2)

    for voting_rule in ordered_rules:
        if voting_rule not in outputs_by_election_type:
            continue

        for n_cands in sorted(outputs_by_election_type[voting_rule].keys(), key=int):
            per_cand = outputs_by_election_type[voting_rule][n_cands]
            for um_key, iia_key in metric_pairs:
                if um_key not in per_cand or iia_key not in per_cand:
                    continue

                scatter_dir = base_dir / f"{int(n_cands)}_cands"
                scatter_dir.mkdir(parents=True, exist_ok=True)
                output_path = build_limited_scatter_plot_name(
                    scatter_dir=scatter_dir,
                    voting_rule=voting_rule,
                    um_key=um_key,
                    iia_key=iia_key,
                    variant_um=variant_um,
                    variant_iia=variant_iia,
                    tiebreak=tiebreak,
                )

                x_data = list(per_cand[um_key])
                y_data = list(per_cand[iia_key])
                overlay_fn = make_bootstrap_overlay(
                    rectangle_lookup=rectangle_lookup,
                    candidate_size=int(n_cands),
                )

                fig, ax = plt.subplots(1, 1, figsize=(8, 8))
                draw_limited_scatter_base(
                    ax=ax,
                    x_data=x_data,
                    y_data=y_data,
                    color=rule_color_map[voting_rule],
                )
                overlay_fn(ax, voting_rule, um_key, iia_key, x_data, y_data)
                plt.savefig(output_path, bbox_inches="tight", dpi=300)
                plt.close(fig)


def main() -> None:
    """Run the limited Scottish scatterplot pipeline with bootstrap overlays."""
    ordered_rules = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]
    variant_um = "worst_case"
    variant_iia = "average"
    tiebreak = "lex"

    top_dir = Path(__file__).resolve().parents[2]
    stats_dir = top_dir / "stats" / "scottish_stats"
    bootstrap_dir = stats_dir / "bootstrap"
    output_dir = top_dir / "plots" / "scottish"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs_by_election_type = load_outputs_by_election_type(
        stats_dir=stats_dir,
        ordered_rules=ordered_rules,
    )
    metric_pairs = get_limited_metric_key_pairs(
        variant_um=variant_um,
        variant_iia=variant_iia,
        tiebreak=tiebreak,
    )
    rectangle_lookup = load_rectangle_lookup(
        bootstrap_dir=bootstrap_dir,
        metric_pairs=metric_pairs,
        tiebreak=tiebreak,
    )
    overlay_fn = make_bootstrap_overlay(
        rectangle_lookup=rectangle_lookup,
        candidate_size=None,
    )

    run_limited_scatter_plots(
        outputs_by_election_type=outputs_by_election_type,
        ordered_rules=ordered_rules,
        output_dir=output_dir,
        variant_um=variant_um,
        variant_iia=variant_iia,
        tiebreak=tiebreak,
        scatter_subdir="scatter_by_voting_rule_with_bootstrap",
        overlay_fn=overlay_fn,
    )

    run_limited_scatter_plots_by_candidate_count_with_bootstrap(
        outputs_by_election_type=outputs_by_election_type,
        ordered_rules=ordered_rules,
        output_dir=output_dir,
        metric_pairs=metric_pairs,
        variant_um=variant_um,
        variant_iia=variant_iia,
        tiebreak=tiebreak,
        rectangle_lookup=rectangle_lookup,
    )


if __name__ == "__main__":
    main()
