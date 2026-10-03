"""Pool saved two-bloc BT scores by alpha tuple, candidate count, and voting rule."""

import argparse
import json
import math
import sys
from itertools import product
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry.plots._data import find_metric_files
from voting_metrics_main_code.constants import (
    BT_ALPHA_COMBINATIONS,
    BT_BLOC_PROPORTIONS,
    BT_CANDIDATE_COMBINATIONS,
    BT_COHESION_COMBINATIONS,
    COMPARISON_RULE_ORDER,
)
from voting_metrics_main_code.replication import ROOT, new_data_file


class AlphaScoreGroup(TypedDict):
    """Raw scores pooled across bloc splits, proportions, and cohesion at fixed total size.

    Source paths are relative to the selected BT statistics root. Scores retain sorted source
    file order and then profile order; each profile contributes one observation.
    """

    alpha: list[float]
    n_cands: int
    rule: str
    source_files: list[str]
    scores: list[float]


def grouped_scores_path(
    stats_root: Path, metric: str, variant: str, interpolation: str, n_seats: int, tiebreak: str
) -> Path:
    """Locate pooled scores without mixing metric, aggregation, interpolation, seats, or ties.

    Args:
        stats_root (Path): Exact pooled statistics directory.
        metric (str): Metric identifier.
        variant (str): Aggregation variant.
        interpolation (str): UM interpolation or 'None' for IIA.
        n_seats (int): Number of elected seats.
        tiebreak (str): Tie-breaking method.

    Returns:
        Path: JSON containing alpha, candidate-count, and voting-rule groups.
    """
    return (
        stats_root
        / f"{n_seats}_seats"
        / (f"METRIC_{metric}__VARIANT_{variant}__INTERP_{interpolation}__TIEBREAK_{tiebreak}.json")
    )


def load_complete_samples(paths: list[str]) -> list[float]:
    """Read nonempty, finite score arrays with equal profile counts across experiments.

    Args:
        paths (list[str]): Source files in concatenation order.

    Returns:
        list[float]: Raw scores, with no averaging or resampling.

    Raises:
        ValueError: A source is empty, nonnumeric, nonfinite, or has a different profile count.
    """
    samples: list[float] = []
    profile_count: int | None = None

    for path in paths:
        with open(path) as source:
            values = json.load(source)

        if (
            not isinstance(values, list)
            or not values
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in values)
        ):
            raise ValueError(f"Expected a nonempty array of finite scores: {path}")
        if profile_count is not None and len(values) != profile_count:
            raise ValueError(f"Profile counts differ across pooled experiments: {path}")

        profile_count = len(values)
        samples.extend(values)

    return samples


def pool_metric_scores(
    bt_stats_root: Path, metric: str, variant: str, interpolation: str, n_seats: int, tiebreak: str
) -> list[AlphaScoreGroup]:
    """Pool a complete configured BT grid while retaining each group's source filenames.

    Args:
        bt_stats_root (Path): Exact two-bloc statistics directory.
        metric (str): Metric identifier.
        variant (str): Aggregation variant.
        interpolation (str): UM interpolation or 'None' for IIA.
        n_seats (int): Number of elected seats.
        tiebreak (str): Tie-breaking method.

    Returns:
        list[AlphaScoreGroup]: Groups sharing the full alpha tuple, total size, and voting rule.

    Raises:
        FileNotFoundError: A configured candidate split has no matching results.
        ValueError: A split lacks the complete proportion/cohesion grid or has invalid scores.
    """
    candidate_totals = sorted({sum(split) for split in BT_CANDIDATE_COMBINATIONS})
    expected_settings = {
        (f"{proportion:.1f}", "(" + ",".join(f"{value:.2f}" for value in cohesion) + ")")
        for proportion, cohesion in product(BT_BLOC_PROPORTIONS, BT_COHESION_COMBINATIONS)
    }
    groups: list[AlphaScoreGroup] = []

    for alpha, n_cands, rule in product(
        BT_ALPHA_COMBINATIONS, candidate_totals, COMPARISON_RULE_ORDER
    ):
        paths: list[str] = []
        for split in BT_CANDIDATE_COMBINATIONS:
            if sum(split) != n_cands:
                continue

            selected = find_metric_files(
                bt_stats_root,
                metric,
                variant,
                interpolation,
                n_seats=n_seats,
                rule=rule,
                tiebreak=tiebreak,
                candidate_counts=split,
                alpha=alpha,
            )
            settings = [
                dict(token.split("_", 1) for token in Path(path).stem.split("__"))
                for path in selected
            ]
            actual_settings = {(fields["BPROP"], fields["COHESION"]) for fields in settings}
            if actual_settings != expected_settings or len(selected) != len(expected_settings):
                raise ValueError(
                    f"Incomplete or duplicate BT grid: {metric}, {alpha}, {split}, {rule}"
                )

            paths.extend(selected)

        paths.sort()
        groups.append(
            AlphaScoreGroup(
                alpha=list(alpha),
                n_cands=n_cands,
                rule=rule,
                source_files=[str(Path(path).relative_to(bt_stats_root)) for path in paths],
                scores=load_complete_samples(paths),
            )
        )

    return groups


def main(
    *,
    bt_stats_root: Path | None = None,
    output_root: Path = ROOT,
    n_seats: int = 3,
    tiebreak: str = "lex",
) -> None:
    """Write pooled inputs for the alpha boxplots, skipping existing result files.

    Args:
        bt_stats_root (Path | None, optional): Exact source tree. None uses the run root's BT stats.
            Defaults to None.
        output_root (Path, optional): Run root containing stats and plots. Defaults to ROOT.
        n_seats (int, optional): Number of elected seats. Defaults to 3.
        tiebreak (str, optional): Tie-breaking method. Defaults to 'lex'.
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or output_root / "stats/bt_2_bloc_profile_stats").resolve()
    stats_root = output_root / "stats/bt_alpha_grouped"
    selections = (
        ("sigma_UM", "asin"),
        ("sigma_UM", "odds"),
        ("sigma_UM_winner_set", "asin"),
        ("sigma_UM_winner_set", "odds"),
        ("sigma_IIA", "None"),
        ("sigma_IIA_winner_set", "None"),
    )

    for (metric, interpolation), variant in product(selections, ("average", "worst_case")):
        destination = grouped_scores_path(
            stats_root, metric, variant, interpolation, n_seats, tiebreak
        )
        if destination.exists() or destination.is_symlink():
            print(f"Skipping existing result: {destination}. Move it manually to rebuild.")
            continue

        groups = pool_metric_scores(
            bt_stats_root, metric, variant, interpolation, n_seats, tiebreak
        )
        with new_data_file(destination) as temporary, temporary.open("w") as output:
            json.dump(groups, output)

        print(f"Saved {len(groups)} groups to {destination}")

    print("Subset IIA is excluded: no saved two-bloc scores are available for that metric.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--n-seats", type=int, default=3)
    parser.add_argument("--tiebreak", choices=("lex", "random"), default="lex")
    args = parser.parse_args()
    main(
        bt_stats_root=args.bt_stats_dir,
        output_root=args.output_dir,
        n_seats=args.n_seats,
        tiebreak=args.tiebreak,
    )
