"""Collect Scottish election statistics across metrics and rules."""

import argparse
import contextlib
import json
import sys
from collections.abc import Mapping
from functools import partial
from glob import escape, glob
from itertools import product
from pathlib import Path
from typing import cast

from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile
from votekit.cvr_loaders import load_scottish

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import RULE_ORDER, AllowedRule
from voting_metrics_main_code.fairness_metric import (
    FairnessMetric,
    sigma_IIA,
    sigma_IIA_winner_set,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import ElectionConstructor, build_voting_rule


def run_score(
    profile_file: str | Path,
    metric_function: FairnessMetric,
    voting_rule: ElectionConstructor,
    n_seats: int,
) -> float:
    """Compute a metric score for a single profile.

    Args:
        profile_file (str | Path): Path to the profile CSV.
        metric_function (FairnessMetric): Metric function to evaluate.
        voting_rule (ElectionConstructor): Voting rule callable.
        n_seats (int): Number of seats to elect.

    Returns:
        float: The computed metric score.
    """
    with contextlib.redirect_stdout(None):
        profile = RankProfile.from_csv(profile_file)
        score = metric_function(cast(RankProfile, profile), voting_rule, n_seats=n_seats)

    return score


def compute_results_single_file(
    election_file: str | Path,
    election_name: AllowedRule,
    metric_function_dict: Mapping[str, FairnessMetric],
    tiebreak: str,
    *,
    seed: int = 0,
) -> dict[str, dict[str, dict[str, float]]]:
    """Compute all metrics for a single Scottish election file.

    Args:
        election_file (str | Path): Path to the election file.
        election_name (AllowedRule): Voting rule name.
        metric_function_dict (Mapping[str, FairnessMetric]): Mapping of metric names to functions.
        tiebreak (str): Tiebreak rule name.
        seed (int, optional): Base seed for independent task streams. Defaults to 0.

    Returns:
        dict[str, dict[str, dict[str, float]]]: Nested dict of candidate counts to metric values.
    """
    election_path = Path(election_file)
    file_name = election_path.stem

    seed_task(election_path.parent.name, election_path.name, election_name, tiebreak, seed=seed)
    output = load_scottish(election_path)
    profile, seats = output[:2]

    n_cands = election_path.parent.name.split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)

    output_dict = {f"{metric_name}_{tiebreak}": {} for metric_name in metric_function_dict.keys()}

    for metric_name, metric_function in metric_function_dict.items():
        output_dict[f"{metric_name}_{tiebreak}"][file_name] = float(
            metric_function(profile, voting_rule, n_seats=seats)
        )

    return {n_cands: output_dict}


def compute_results_single_file_and_metric(
    election_file: str | Path,
    election_name: AllowedRule,
    metric_function_dict: Mapping[str, FairnessMetric],
    metric_name: str,
    tiebreak: str,
    *,
    seed: int = 0,
) -> tuple[str, str, float]:
    """Compute a single metric for one election file.

    Args:
        election_file (str | Path): Path to the election file.
        election_name (AllowedRule): Voting rule name.
        metric_function_dict (Mapping[str, FairnessMetric]): Mapping of metric names to functions.
        metric_name (str): Metric key to compute.
        tiebreak (str): Tiebreak rule name.
        seed (int, optional): Base seed for independent task streams. Defaults to 0.

    Returns:
        tuple[str, str, float]: Candidate count, file stem, and metric value.
    """
    election_path = Path(election_file)
    file_name = election_path.stem

    seed_task(election_path.parent.name, election_path.name, election_name, tiebreak, seed=seed)
    output = load_scottish(election_path)
    profile, seats = output[:2]

    n_cands = election_path.parent.name.split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)

    return (
        n_cands,
        file_name,
        metric_function_dict[metric_name](profile, voting_rule, n_seats=seats),
    )


# =================================================================


def main(
    *, data_root: Path = ROOT / "data", output_root: Path = ROOT, seed: int = 0, n_jobs: int = 1
) -> None:
    """Save primary Scottish metrics by rule and tiebreak, skipping existing output files.

    Args:
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        seed (int, optional): Base seed for independent task streams. Defaults to 0.
        n_jobs (int, optional): Number of parallel workers. Defaults to 1.

    Raises:
        ValueError: No Scottish election CSVs match the supported candidate counts.
    """
    output_root = output_root.resolve()
    data_root = data_root.resolve()
    if n_jobs < 1:
        raise ValueError("n_jobs must be positive")

    stats_dir = (output_root / "stats/scottish_stats").resolve()
    stats_dir.mkdir(parents=True, exist_ok=True)

    candidate_range = range(3, 15)

    all_files = glob(f"{escape(str(data_root))}/scot-elex/*/*.csv")
    all_files = [
        path for path in all_files if any(f"/{count}_cands" in path for count in candidate_range)
    ]

    metric_function_dict = {
        "sigma_UM_worst_case_asin": partial(
            sigma_UM, variant="worst_case", interpolation_type="asin"
        ),
        "sigma_UM_winner_set_worst_case_asin": partial(
            sigma_UM_winner_set, variant="worst_case", interpolation_type="asin"
        ),
        "sigma_IIA_average": partial(sigma_IIA, variant="average"),
        "sigma_IIA_winner_set_average": partial(sigma_IIA_winner_set, variant="average"),
    }
    all_election_types = RULE_ORDER
    tiebreak_types = ["lex", "random"]

    if not all_files:
        raise ValueError(f"No Scottish election CSVs found under {data_root / 'scot-elex'}")

    all_files.sort()

    for metric, election_name, tiebreak in product(
        metric_function_dict.keys(), all_election_types, tiebreak_types
    ):
        output_folder = stats_dir / metric / election_name
        output_folder.mkdir(parents=True, exist_ok=True)
        output_file = (
            output_folder
            / f"METRIC_{metric}__ELECTION_TYPE_{election_name}__TIEBREAK_{tiebreak}_output.json"
        )

        if output_file.exists() or output_file.is_symlink():
            print(f"Skipping existing result: {output_file}. Move it manually to recompute.")
            continue

        with joblib_progress(
            total=len(all_files),
            description=f"Collecting stats for {metric}, {election_name}, {tiebreak}",
        ):
            # Joblib does not retain the worker's tuple type in its return annotation.
            results = cast(
                list[tuple[str, str, float]],
                Parallel(n_jobs=n_jobs)(
                    delayed(compute_results_single_file_and_metric)(
                        path, election_name, metric_function_dict, metric, tiebreak, seed=seed
                    )
                    for path in all_files
                ),
            )

        cand_counts = {n_cands for n_cands, _, _ in results}
        output_dict = {n_cands: {} for n_cands in cand_counts}

        for n_cands, file_name, value in results:
            output_dict[n_cands][file_name] = value

        with new_data_file(output_file) as temporary_file, temporary_file.open("w") as scores_file:
            json.dump(output_dict, scores_file, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-jobs", type=int, default=1)
    args = parser.parse_args()
    main(data_root=args.data_dir, output_root=args.output_dir, seed=args.seed, n_jobs=args.n_jobs)
