"""Collect Scottish election statistics across metrics and rules."""

import contextlib
from functools import partial
import json
import sys
from glob import glob
from itertools import product
from pathlib import Path
from typing import Mapping, Protocol, cast

from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile
from votekit.cvr_loaders import load_scottish

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import RULE_ORDER
from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_all_subset,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.replication import DATA_DIR, N_JOBS, STATS_OUTPUT, seed_task
from voting_metrics_main_code.voting_rules import ElectionConstructor, build_voting_rule


class MetricFn(Protocol):
    """Callable signature for metric functions used in this pipeline."""

    def __call__(
        self, profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        """Evaluate the configured metric for a profile, voting rule, and seat count.

        Args:
            profile (RankProfile): Ranked-ballot preference profile.
            voting_rule (ElectionConstructor): Voting rule callable passed to the metric.
            n_seats (int): Number of seats to elect.

        Returns:
            float: Metric score for the supplied election configuration.
        """
        ...


def run_score(
    profile_file: str | Path,
    metric_function: MetricFn,
    voting_rule: ElectionConstructor,
    n_seats: int,
) -> float:
    """Compute a metric score for a single profile.

    Args:
        profile_file (str | Path): Path to the profile CSV.
        metric_function (MetricFn): Metric function to evaluate.
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
    f: str | Path,
    election_name: str,
    metric_function_dict: Mapping[str, MetricFn],
    tiebreak: str,
) -> dict[str, dict[str, dict[str, float]]]:
    """Compute all metrics for a single Scottish election file.

    Args:
        f (str | Path): Path to the election file.
        election_name (str): Voting rule name.
        metric_function_dict (Mapping[str, MetricFn]): Mapping of metric names to functions.
        tiebreak (str): Tiebreak rule name.

    Returns:
        dict[str, dict[str, dict[str, float]]]: Nested dict of candidate counts to metric values.
    """
    file_name = str(Path(f).stem)

    seed_task(Path(f).parent.name, Path(f).name, election_name, tiebreak)
    output = load_scottish(f)
    profile, seats = output[:2]

    n_cands = str(f).split("/")[-2].split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)  # ty: ignore

    output_dict = {f"{metric_name}_{tiebreak}": {} for metric_name in metric_function_dict.keys()}

    for metric_name, metric_function in metric_function_dict.items():
        output_dict[f"{metric_name}_{tiebreak}"][file_name] = float(
            metric_function(profile, voting_rule, n_seats=seats)
        )

    return {n_cands: output_dict}


def compute_results_single_file_and_metric(
    f: str | Path,
    election_name: str,
    metric_function_dict: Mapping[str, MetricFn],
    metric_name: str,
    tiebreak: str,
) -> tuple[str, str, float]:
    """Compute a single metric for one election file.

    Args:
        f (str | Path): Path to the election file.
        election_name (str): Voting rule name.
        metric_function_dict (Mapping[str, MetricFn]): Mapping of metric names to functions.
        metric_name (str): Metric key to compute.
        tiebreak (str): Tiebreak rule name.

    Returns:
        tuple[str, str, float]: Candidate count, file stem, and metric value.
    """
    file_name = str(Path(f).stem)

    seed_task(Path(f).parent.name, Path(f).name, election_name, tiebreak)
    output = load_scottish(f)
    profile, seats = output[:2]

    n_cands = str(f).split("/")[-2].split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)  # type: ignore

    return (
        n_cands,
        file_name,
        metric_function_dict[metric_name](profile, voting_rule, n_seats=seats),
    )


# =================================================================


def sigma_UM_worst_case_asin() -> MetricFn:
    """Wrap sigma_UM with worst-case ASIN interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM, variant="worst_case", interpolation_type="asin")


def sigma_UM_average_asin() -> MetricFn:
    """Wrap sigma_UM with average-case ASIN interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM, variant="average", interpolation_type="asin")


def sigma_UM_worst_case_odds() -> MetricFn:
    """Wrap sigma_UM with worst-case odds interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM, variant="worst_case", interpolation_type="odds")


def sigma_UM_average_odds() -> MetricFn:
    """Wrap sigma_UM with average-case odds interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM, variant="average", interpolation_type="odds")


def sigma_UM_winner_set_worst_case_asin() -> MetricFn:
    """Wrap sigma_UM_winner_set with worst-case ASIN interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM_winner_set, variant="worst_case", interpolation_type="asin")


def sigma_UM_winner_set_average_asin() -> MetricFn:
    """Wrap sigma_UM_winner_set with average-case ASIN interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM_winner_set, variant="average", interpolation_type="asin")


def sigma_UM_winner_set_worst_case_odds() -> MetricFn:
    """Wrap sigma_UM_winner_set with worst-case odds interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM_winner_set, variant="worst_case", interpolation_type="odds")


def sigma_UM_winner_set_average_odds() -> MetricFn:
    """Wrap sigma_UM_winner_set with average-case odds interpolation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_UM_winner_set, variant="average", interpolation_type="odds")


# =================================================================


def sigma_IIA_worst_case() -> MetricFn:
    """Wrap sigma_IIA with worst-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA, variant="worst_case")


def sigma_IIA_average() -> MetricFn:
    """Wrap sigma_IIA with average-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA, variant="average")


def sigma_IIA_all_subset_worst_case() -> MetricFn:
    """Wrap sigma_IIA_all_subset with worst-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_all_subset, variant="worst_case")


def sigma_IIA_all_subset_average() -> MetricFn:
    """Wrap sigma_IIA_all_subset with average-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_all_subset, variant="average")


def sigma_IIA_winner_set_worst_case() -> MetricFn:
    """Wrap sigma_IIA_winner_set with worst-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_winner_set, variant="worst_case")


def sigma_IIA_winner_set_average() -> MetricFn:
    """Wrap sigma_IIA_winner_set with average-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_winner_set, variant="average")


def sigma_IIA_winner_set_all_subset_worst_case() -> MetricFn:
    """Wrap sigma_IIA_winner_set_all_subset with worst-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_winner_set_all_subset, variant="worst_case")


def sigma_IIA_winner_set_all_subset_average() -> MetricFn:
    """Wrap sigma_IIA_winner_set_all_subset with average-case aggregation.

    Returns:
        MetricFn: Callable accepting profile, voting_rule, and n_seats with this configuration.
    """
    return partial(sigma_IIA_winner_set_all_subset, variant="average")


def main() -> None:
    """Save primary Scottish metrics by rule and tiebreak, skipping existing output files.

    Raises:
        ValueError: No Scottish election CSVs match the supported candidate counts.
    """
    output_folder = Path(f"{STATS_OUTPUT}/scottish_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    candidate_range = range(3, 15)

    all_files = glob(f"{DATA_DIR}/scot-elex/*/*.csv")
    all_files = [f for f in all_files if any([f"/{i}_cands" in f for i in candidate_range])]

    metric_function_dict = {
        "sigma_UM_worst_case_asin": sigma_UM_worst_case_asin(),
        "sigma_UM_winner_set_worst_case_asin": sigma_UM_winner_set_worst_case_asin(),
        "sigma_IIA_average": sigma_IIA_average(),
        "sigma_IIA_winner_set_average": sigma_IIA_winner_set_average(),
    }
    all_election_types = RULE_ORDER
    tiebreak_types = ["lex", "random"]

    if not all_files:
        raise ValueError(f"No Scottish election CSVs found under {DATA_DIR / 'scot-elex'}")

    all_files.sort()

    for metric, election_name, tiebreak in product(
        metric_function_dict.keys(), all_election_types, tiebreak_types
    ):
        output_folder = Path(f"{output_folder_base}/{metric}/{election_name}")
        output_folder.mkdir(parents=True, exist_ok=True)
        output_file = (
            output_folder
            / f"METRIC_{metric}__ELECTION_TYPE_{election_name}__TIEBREAK_{tiebreak}_output.json"
        )

        if output_file.exists():
            print(f"Skipping {output_file}, already exists.")
            continue

        with joblib_progress(
            total=len(all_files),
            description=f"Collecting stats for {metric}, {election_name}, {tiebreak}",
        ):
            results = Parallel(n_jobs=N_JOBS)(
                delayed(compute_results_single_file_and_metric)(
                    f, election_name, metric_function_dict, metric, tiebreak
                )
                for f in all_files
            )

        cand_counts = set(x[0] for x in results)
        output_dict = {n_cands: {} for n_cands in cand_counts}

        for n_cands, file_name, value in results:
            output_dict[n_cands][file_name] = value

        with open(output_file, "w") as f:
            json.dump(output_dict, f, indent=4)


if __name__ == "__main__":
    main()
