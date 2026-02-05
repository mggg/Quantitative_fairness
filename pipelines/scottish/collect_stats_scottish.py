"""Collect Scottish election statistics across metrics and rules."""

import contextlib
from glob import glob
from itertools import product
import json
from pathlib import Path
import sys
from typing import Mapping, Protocol, cast

from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile
from votekit.cvr_loaders import load_scottish


sys.path.append(str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_all_subset,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.voting_rules import ElectionConstructor, build_voting_rule


class MetricFn(Protocol):
    """Callable signature for metric functions used in this pipeline."""

    def __call__(
        self, profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float: ...


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
        score = metric_function(
            cast(RankProfile, profile), voting_rule, n_seats=n_seats
        )
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
        metric_function_dict (Mapping[str, MetricFn]): Mapping of metric names to
            functions.
        tiebreak (str): Tiebreak rule name.

    Returns:
        dict[str, dict[str, dict[str, float]]]: Nested dict of candidate counts to
            metric values.
    """
    file_name = str(Path(f).stem)

    output = load_scottish(f)
    profile, seats = output[:2]

    n_cands = str(f).split("/")[-2].split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)  # ty: ignore

    output_dict = {
        f"{metric_name}_{tiebreak}": {} for metric_name in metric_function_dict.keys()
    }

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
        metric_function_dict (Mapping[str, MetricFn]): Mapping of metric names to
            functions.
        metric_name (str): Metric key to compute.
        tiebreak (str): Tiebreak rule name.

    Returns:
        tuple[str, str, float]: Candidate count, file stem, and metric value.
    """
    file_name = str(Path(f).stem)

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
    """Wrap sigma_UM with worst-case ASIN interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="worst_case",
            interpolation_type="asin",
        )

    return wrapper


def sigma_UM_average_asin() -> MetricFn:
    """Wrap sigma_UM with average-case ASIN interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="average",
            interpolation_type="asin",
        )

    return wrapper


def sigma_UM_worst_case_odds() -> MetricFn:
    """Wrap sigma_UM with worst-case odds interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="worst_case",
            interpolation_type="odds",
        )

    return wrapper


def sigma_UM_average_odds() -> MetricFn:
    """Wrap sigma_UM with average-case odds interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="average",
            interpolation_type="odds",
        )

    return wrapper


def sigma_UM_winner_set_worst_case_asin() -> MetricFn:
    """Wrap sigma_UM_winner_set with worst-case ASIN interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM_winner_set(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="worst_case",
            interpolation_type="asin",
        )

    return wrapper


def sigma_UM_winner_set_average_asin() -> MetricFn:
    """Wrap sigma_UM_winner_set with average-case ASIN interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM_winner_set(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="average",
            interpolation_type="asin",
        )

    return wrapper


def sigma_UM_winner_set_worst_case_odds() -> MetricFn:
    """Wrap sigma_UM_winner_set with worst-case odds interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM_winner_set(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="worst_case",
            interpolation_type="odds",
        )

    return wrapper


def sigma_UM_winner_set_average_odds() -> MetricFn:
    """Wrap sigma_UM_winner_set with average-case odds interpolation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_UM_winner_set(
            profile,
            voting_rule,
            n_seats=n_seats,
            variant="average",
            interpolation_type="odds",
        )

    return wrapper


# =================================================================


def sigma_IIA_worst_case() -> MetricFn:
    """Wrap sigma_IIA with worst-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA(profile, voting_rule, n_seats=n_seats, variant="worst_case")

    return wrapper


def sigma_IIA_average() -> MetricFn:
    """Wrap sigma_IIA with average-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA(profile, voting_rule, n_seats=n_seats, variant="average")

    return wrapper


def sigma_IIA_all_subset_worst_case() -> MetricFn:
    """Wrap sigma_IIA_all_subset with worst-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_all_subset(
            profile, voting_rule, n_seats=n_seats, variant="worst_case"
        )

    return wrapper


def sigma_IIA_all_subset_average() -> MetricFn:
    """Wrap sigma_IIA_all_subset with average-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_all_subset(
            profile, voting_rule, n_seats=n_seats, variant="average"
        )

    return wrapper


def sigma_IIA_winner_set_worst_case() -> MetricFn:
    """Wrap sigma_IIA_winner_set with worst-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_winner_set(
            profile, voting_rule, n_seats=n_seats, variant="worst_case"
        )

    return wrapper


def sigma_IIA_winner_set_average() -> MetricFn:
    """Wrap sigma_IIA_winner_set with average-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_winner_set(
            profile, voting_rule, n_seats=n_seats, variant="average"
        )

    return wrapper


def sigma_IIA_winner_set_all_subset_worst_case() -> MetricFn:
    """Wrap sigma_IIA_winner_set_all_subset with worst-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_winner_set_all_subset(
            profile, voting_rule, n_seats=n_seats, variant="worst_case"
        )

    return wrapper


def sigma_IIA_winner_set_all_subset_average() -> MetricFn:
    """Wrap sigma_IIA_winner_set_all_subset with average-case aggregation."""

    def wrapper(
        profile: RankProfile, voting_rule: ElectionConstructor, n_seats: int
    ) -> float:
        return sigma_IIA_winner_set_all_subset(
            profile, voting_rule, n_seats=n_seats, variant="average"
        )

    return wrapper


if __name__ == "__main__":
    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of statistics are not overwritten.
    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/scottish_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    # WARN: Change this for different candidate ranges
    candidate_range = range(3, 15)

    all_files = glob(f"{top_dir}/data/scot-elex/*/*.csv")
    all_files = [
        f for f in all_files if any([f"/{i}_cands" in f for i in candidate_range])
    ]

    metric_function_dict = {
        "sigma_UM_worst_case_asin": sigma_UM_worst_case_asin(),
        "sigma_UM_average_asin": sigma_UM_average_asin(),
        "sigma_UM_worst_case_odds": sigma_UM_worst_case_odds(),
        "sigma_UM_average_odds": sigma_UM_average_odds(),
        "sigma_UM_winner_set_worst_case_asin": sigma_UM_winner_set_worst_case_asin(),
        "sigma_UM_winner_set_average_asin": sigma_UM_winner_set_average_asin(),
        "sigma_UM_winner_set_worst_case_odds": sigma_UM_winner_set_worst_case_odds(),
        "sigma_UM_winner_set_average_odds": sigma_UM_winner_set_average_odds(),
        "sigma_IIA_worst_case": sigma_IIA_worst_case(),
        "sigma_IIA_average": sigma_IIA_average(),
        "sigma_IIA_all_subset_worst_case": sigma_IIA_all_subset_worst_case(),
        "sigma_IIA_all_subset_average": sigma_IIA_all_subset_average(),
        "sigma_IIA_winner_set_worst_case": sigma_IIA_winner_set_worst_case(),
        "sigma_IIA_winner_set_average": sigma_IIA_winner_set_average(),
        "sigma_IIA_winner_set_all_subset_worst_case": sigma_IIA_winner_set_all_subset_worst_case(),
        "sigma_IIA_winner_set_all_subset_average": sigma_IIA_winner_set_all_subset_average(),
    }
    all_election_types = [
        # "borda",
        # "3-approval",
        # "2-approval",
        # "plurality",
        # "stv",
        # "ranked-pairs",
        "random",
    ]
    tiebreak_types = ["lex", "random"]
    file_to_column_data_dict = {}

    for f in all_files[:]:
        file_name = str(Path(f).stem)
        file_to_column_data_dict[file_name] = dict()

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
            results = Parallel(n_jobs=-1)(
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

    # for election_name in all_election_types:
    #     scottish_election_stats = {
    #         str(cands): {
    #             f"{metric_name}_{tiebreak}": {}
    #             for metric_name, tiebreak in product(
    #                 metric_function_dict.keys(), tiebreak_types
    #             )
    #         }
    #         for cands in candidate_range
    #     }
    #     for tiebreak in tiebreak_types:

    #         with joblib_progress(
    #             total=len(all_files),
    #             description=f"Collecting stats for {election_name}, tiebreak={tiebreak}",
    #         ):
    #             results = Parallel(n_jobs=28)(
    #                 delayed(compute_results_single_file)(
    #                     f, election_name, metric_function_dict, tiebreak
    #                 )
    #                 for f in all_files
    #             )

    #         for output_dict in results:
    #             assert output_dict is not None
    #             for n_cands, data in output_dict.items():
    #                 for key, value_dict in data.items():
    #                     scottish_election_stats[n_cands][key].update(value_dict)

    #     # Save the full output
    #     output_file = f"{output_folder_base}/{election_name}_output.json"
    #     with open(output_file, "w") as f:
    #         json.dump(scottish_election_stats, f, indent=4)
    #     with open(output_file, "r") as f:
    #         scottish_election_stats = json.load(f)

    #     # Now for the stats we care about
    #     scottish_election_interpreted_values = {
    #         str(cands): {} for cands in candidate_range
    #     }

    #     for key, data_dict in scottish_election_stats.items():
    #         if data_dict == {
    #             f"{metric}_{tiebreak}": {}
    #             for metric, tiebreak in product(
    #                 metric_function_dict.keys(), tiebreak_types
    #             )
    #         }:
    #             print(f"No data for {key}, skipping.")
    #             continue

    #         for metric_name, tiebreak in product(
    #             metric_function_dict.keys(), tiebreak_types
    #         ):
    #             metric_data_list = list(data_dict[f"{metric_name}_{tiebreak}"].values())
    #             scottish_election_interpreted_values[key][
    #                 f"mean_{metric_name}_{tiebreak}"
    #             ] = float(np.mean(metric_data_list))
    #             scottish_election_interpreted_values[key][
    #                 f"std_dev_{metric_name}_{tiebreak}"
    #             ] = float(np.std(metric_data_list))

    #     stats_file = f"{output_folder_base}/{election_name}_stats.json"
    #     with open(stats_file, "w") as f:
    #         json.dump(scottish_election_interpreted_values, f, indent=4)

    #     for f in all_files:
    #         file_name = str(Path(f).stem)
    #         n_cands = f.split("/")[-2].split("_")[0]

    #         data = {
    #             "n_cands": n_cands,
    #         } | {
    #             metric: scottish_election_stats[n_cands][f"{metric}_{tiebreak}"][
    #                 file_name
    #             ]
    #             for metric, tiebreak in product(
    #                 metric_function_dict.keys(), tiebreak_types
    #             )
    #         }

    #         file_to_column_data_dict[file_name][election_name] = data

    # df = pd.concat(
    #     {
    #         file_name: pd.DataFrame(methods_dict).T
    #         for file_name, methods_dict in file_to_column_data_dict.items()
    #     }
    # )

    # # Move ward and method into columns instead of MultiIndex
    # df.index.names = ["election_name", "method"]
    # df = df.reset_index()
    # df.to_csv(
    #     f"{output_folder_base}/scottish_stats_tagged_by_election.csv", index=False
    # )
