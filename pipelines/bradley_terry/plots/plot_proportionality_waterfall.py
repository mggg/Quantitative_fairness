"""This script generates waterfall plots for the Bradley-Terry proportionality analysis."""

import argparse
import json
import sys
from collections.abc import Sequence
from glob import escape, glob
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import (
    ALT_FONT_SIZES,
    BT_ALPHA_COMBINATIONS,
    BT_BLOC_PROPORTIONS,
    BT_CANDIDATE_COMBINATIONS,
    BT_COHESION_COMBINATIONS,
    DEFAULT_FONT_SIZE,
)
from voting_metrics_main_code.constants import (
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.constants import (
    RULE_ORDER as AllowedRule,
)
from voting_metrics_main_code.replication import ROOT


def profile_settings() -> list[str]:
    """Enumerate the two-bloc parameter settings used in proportionality comparisons.

    Returns:
        list[str]: Profile setting path suffixes in grid order.
    """
    b_bloc_proportions = BT_BLOC_PROPORTIONS
    alpha_combinations = BT_ALPHA_COMBINATIONS
    cohesion_combinations = BT_COHESION_COMBINATIONS
    candidate_count_combinations = BT_CANDIDATE_COMBINATIONS

    settings = []

    for (n_a_cands, n_b_cands), b_bloc_proportion, (a_coh, b_coh), (
        aa_al,
        ab_al,
        ba_al,
        bb_al,
    ) in product(
        candidate_count_combinations,
        b_bloc_proportions,
        cohesion_combinations,
        alpha_combinations,
    ):
        settings_str = (
            f"{n_a_cands:02d}_{n_b_cands:02d}/"
            f"b_proportion_{b_bloc_proportion}"
            f"__ALPHA_({aa_al:.2f},{ab_al:.2f},{ba_al:.2f},{bb_al:.2f})"
            f"__COHESION_({a_coh:.2f},{b_coh:.2f})"
        )

        settings.append(settings_str)

    return settings


def load_proportionality_statistics(*, stats_root: Path) -> pd.DataFrame:
    """Load proportionality JSONs into one row per profile and voting rule.

    Returns:
        pd.DataFrame: Columns file, method, expected_proportion, and observed_proportion. The file
            column contains the candidate-count and bloc-setting directory suffix.

    Raises:
        FileNotFoundError: No proportionality JSON files exist in the configured input directory.
        json.JSONDecodeError: A proportionality input file is not valid JSON.

    Args:
        stats_root (Path): Parent of the dataset statistics directories.
    """
    all_files = glob(f"{escape(str(stats_root))}/bt_proportionality/*.json")

    if not all_files:
        raise FileNotFoundError(
            f"No proportionality JSON files under {stats_root / 'bt_proportionality'}"
        )

    df_list = []

    for path in all_files:
        with open(path, "r") as f:
            data = json.load(f)

        rows = []

        for file_path, methods in data.items():
            for method, vals in methods.items():
                rows.append(
                    {
                        "file": file_path,
                        "method": method,
                        "expected_proportion": vals.get("expected_proportion"),
                        "observed_proportion": vals.get("observed_proportion"),
                    }
                )

        df_list.append(pd.DataFrame(rows))

    df = pd.concat(df_list, ignore_index=True)
    df["file"] = df["file"].map(lambda path: "/".join(Path(path).parts[-3:-1]))

    return df


def aggregate_proportionality_points(
    statistics: pd.DataFrame, settings: Sequence[str]
) -> tuple[list[float], list[float]]:
    """Compute expected and mean observed representation in the selected setting order.

    Args:
        statistics (pd.DataFrame): Proportionality rows already filtered to one voting rule.
        settings (Sequence[str]): Profile setting suffixes in plotting order.

    Returns:
        tuple[list[float], list[float]]: Expected proportions followed by mean observed proportions.

    Raises:
        KeyError: A requested setting has no rows in statistics.
    """
    grouped = statistics.groupby("file", sort=False)
    all_x_values = []
    all_y_values = []

    for pat in settings:
        filtered = grouped.get_group(pat)

        all_x_values.append(
            float(filtered["expected_proportion"].iloc[0])
        )  # They are all the same for a given setting

        all_y_values.append(float(filtered["observed_proportion"].to_numpy().mean()))

    return all_x_values, all_y_values


def plot_rule_waterfall(
    df: pd.DataFrame, election_type: str, all_settings_strings: Sequence[str], output_dir: Path
) -> None:
    """Save one rule’s expected-versus-observed bloc representation waterfall.

    Args:
        df (pd.DataFrame): Proportionality rows with file, method, and expected/observed
            proportions.
        election_type (str): Voting rule name.
        all_settings_strings (Sequence[str]): Profile setting suffixes in plotting order.
        output_dir (Path): Directory for generated figures.

    Raises:
        KeyError: A requested profile setting has no rows for the selected rule.
    """
    n_seats = 3
    rule_df = df.query("method == @election_type")
    _, ax = plt.subplots(1, 1, figsize=(8, 8))

    all_x_values, all_y_values = aggregate_proportionality_points(rule_df, all_settings_strings)

    points = list(zip(all_x_values, all_y_values))

    ax.plot(
        all_x_values,
        all_y_values,
        color=rule_color_map[election_type],
        marker="o",
        linestyle="None",
    )

    boxes = [(i / n_seats, (i + 1) / n_seats) for i in range(n_seats + 1)]

    def is_point_in_box(point: tuple[float, float], box: tuple[float, float]) -> bool:
        """Check whether both point coordinates lie within one interval, allowing rounding error.

        Args:
            point (tuple[float, float]): Expected and observed proportions.
            box (tuple[float, float]): Lower and upper bounds shared by both axes.

        Returns:
            bool: Whether both coordinates are within the bounds with tolerance 1e-12.
        """
        # Needed to deal with floating point precision issues when checking if a point is in a box
        eps = 1e-12

        return box[0] - eps <= point[0] <= box[1] + eps and box[0] - eps <= point[1] <= box[1] + eps

    points_in_boxes = sum(
        1 for point in points if any(is_point_in_box(point, box) for box in boxes)
    )

    election_type_str = f"Election type: {election_type:>12}"
    points_in_boxes_str = f"Points in boxes: {points_in_boxes} / {len(points)}"
    print(f"{election_type_str:<20}, {points_in_boxes_str:<50}")

    ax.step(
        np.linspace(0, 1, n_seats + 1),
        np.arange(0, 1.1, 1 / n_seats),
        linestyle="dashed",
        c="gray",
        where="pre",
    )
    ax.step(
        np.linspace(0, 1, n_seats + 1),
        np.arange(0, 1.1, 1 / n_seats),
        linestyle="dashed",
        c="gray",
        where="post",
    )

    ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    ax.set_xlim(min(ticks) - 0.01, max(ticks) + 0.01)
    ax.set_ylim(min(ticks) - 0.01, max(ticks) + 0.01)

    ax.set_xticks(
        ticks,
        labels=[f"{tick:.1f}" for tick in ticks],
        fontsize=ALT_FONT_SIZES.get(election_type, DEFAULT_FONT_SIZE),
    )
    ax.set_yticks(
        ticks,
        labels=[f"{tick:.1f}" for tick in ticks],
        fontsize=ALT_FONT_SIZES.get(election_type, DEFAULT_FONT_SIZE),
    )

    ax.set_aspect("equal", adjustable="box")
    # print(f"Saving {election_type} waterfall plot...")
    plt.savefig(
        output_dir / f"{election_type}_waterfall.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


def main(*, stats_root: Path | None = None, output_root: Path = ROOT) -> None:
    """Load proportionality statistics and save a waterfall for each configured voting rule.

    Raises:
        FileNotFoundError: No proportionality JSON files exist in the configured input directory.

    Args:
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()
    print(f"Statistics: {stats_root}")
    print(f"Output root: {output_root}")

    all_settings_strings = profile_settings()

    df = load_proportionality_statistics(stats_root=stats_root)
    output_dir = output_root / "plots" / "bt_plots/waterfall"
    output_dir.mkdir(parents=True, exist_ok=True)

    for election_type in AllowedRule:
        plot_rule_waterfall(df, election_type, all_settings_strings, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(stats_root=args.stats_dir, output_root=args.output_dir)
