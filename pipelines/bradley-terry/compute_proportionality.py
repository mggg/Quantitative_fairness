"""Compute proportionality diagnostics for BT preference profiles."""

from glob import glob
import json
from pathlib import Path
import sys
from typing import get_args

import click
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
import pandas as pd
from votekit import RankProfile, PreferenceProfile
from votekit.ballot_generator import BlocSlateConfig

sys.path.append(str(Path(__file__).resolve().parents[2]))

from voting_rules import build_voting_rule, AllowedRule

TOP_DIR = Path(__file__).resolve().parents[2]


def load_one(path: str) -> tuple[str, PreferenceProfile]:
    """Load a preference profile from a CSV file.

    Args:
        path (str): The path to the CSV file.

    Returns:
        tuple[str, PreferenceProfile]: A tuple containing the file path and the loaded PreferenceProfile.
    """
    return path, RankProfile.from_csv(path)


def get_all_profiles(
    n_a_cand: int,
    n_b_cand: int,
    b_prop: float,
    a_coh: float,
    b_coh: float,
) -> dict[str, PreferenceProfile]:
    """Get all preference profiles based on given parameters.

    Args:
        n_a_cand (int): Number of A candidates.
        n_b_cand (int): Number of B candidates.
        b_prop (float): Proportion of B voters.
        a_coh (float): Cohesion of A voters.
        b_coh (float): Cohesion of B voters.

    Returns:
        dict[str, PreferenceProfile]: A dictionary mapping file paths to PreferenceProfiles.
    """
    search_string = (
        f"{TOP_DIR}/data/preference_profiles/{n_a_cand:02d}_{n_b_cand:02d}/"
        f"b_proportion_{b_prop:0.1f}__ALPHA_(*)__COHESION_({a_coh:0.2f},{b_coh:0.2f})/*.csv"
    )
    profile_files = sorted(glob(search_string))

    with joblib_progress(total=len(profile_files)):
        pairs = Parallel(n_jobs=-1, prefer="processes", batch_size="auto")(
            delayed(load_one)(p) for p in profile_files
        )

    all_profiles = dict(pairs)
    return all_profiles


def frsp(r: int, s: int, rho: float) -> float:
    """Calculate the probability of one slate putting another slate first.

    Args:
        r (int): Number of candidates in the first slate.
        s (int): Number of candidates in the second slate.
        rho (float): Cohesion parameter.

    Returns:
        float: The calculated probability.
    """
    return 1 - (1 - rho**s) / (1 - rho ** (r + s))


def process_profile(
    file: str, profile: PreferenceProfile
) -> dict[str, dict[str, dict[str, float]]]:
    """Process a preference profile and calculate various metrics.

    Args:
        file (str): The path to the preference profile file.
        profile (PreferenceProfile): The loaded PreferenceProfile.

    Returns:
        dict[str, dict[str, dict[str, float]]]: A dictionary containing processed data for the given file.
    """
    utility_file = file.replace("preference_profiles", "preference_dfs").replace(
        ".csv", "_utilities.csv"
    )
    utility_df = pd.read_csv(utility_file, index_col=0)
    ranking_df = pd.read_csv(file, skiprows=list(range(8)))

    a_cohesion, b_cohesion = list(
        map(float, file.split("_COHESION_(")[1].split(")/")[0].split(","))
    )
    b_proportion = float(file.split("b_proportion_")[1].split("__")[0])

    counts = {"A": 0, "B": 0}
    slate_to_candidates: dict[str, list[str]] = {"bloc_1": [], "bloc_2": []}

    n_a_candidates, n_b_candidates = list(
        map(int, file.split("preference_profiles/")[1].split("/")[0].split("_"))
    )
    n_cands = n_a_candidates + n_b_candidates
    slate_to_candidates = {
        "bloc_1": [f"A{i}" for i in range(1, n_a_candidates + 1)],
        "bloc_2": [f"B{j}" for j in range(1, n_b_candidates + 1)],
    }

    for _, fpv, weight in ranking_df[["Ranking_1", "Weight"]].itertuples():
        cand = fpv[2:4]
        counts[cand[0]] += int(weight)

    n_voters = int(ranking_df["Weight"].sum())

    config = BlocSlateConfig(
        n_voters=n_voters,
        slate_to_candidates=slate_to_candidates,
        cohesion_mapping={
            "bloc_1": {"bloc_1": a_cohesion, "bloc_2": 1 - a_cohesion},
            "bloc_2": {"bloc_1": 1 - b_cohesion, "bloc_2": b_cohesion},
        },
        bloc_proportions={"bloc_1": 1 - b_proportion, "bloc_2": b_proportion},
        preference_mapping=utility_df,
    )
    config.normalize_preference_intervals()
    n_b_voters = int(b_proportion * n_voters)
    n_a_voters = n_voters - n_b_voters
    n_a_candidates = len(slate_to_candidates["bloc_1"])
    n_b_candidates = len(slate_to_candidates["bloc_2"])

    prob_b_puts_b_first = frsp(
        n_b_candidates, n_a_candidates, b_cohesion / (1 - b_cohesion)
    )
    prob_a_puts_a_first = frsp(
        n_a_candidates, n_b_candidates, a_cohesion / (1 - a_cohesion)
    )

    expected_b_fpv = n_b_voters * prob_b_puts_b_first + n_a_voters * (
        1 - prob_a_puts_a_first
    )
    expected_b_win_prorportion = expected_b_fpv / n_voters

    file_to_rule_dict = {}
    for voting_rule_name in get_args(AllowedRule):
        rule = build_voting_rule(n_cands=n_cands, voting_rule_name=voting_rule_name)
        winners = rule(profile, m=3).get_elected()
        b_winners = [c for c in winners if next(iter(c)).startswith("B")]
        b_win_proportion = len(b_winners) / len(winners)
        file_to_rule_dict[voting_rule_name] = {
            "expected_proportion": expected_b_win_prorportion,
            "observed_proportion": b_win_proportion,
        }

    return {file: file_to_rule_dict}


@click.command()
@click.option("--n-a-cand", type=int, required=True, help="Number of A candidates")
@click.option("--n-b-cand", type=int, required=True, help="Number of B candidates")
@click.option(
    "--b-prop",
    type=float,
    required=True,
    help="Proportion of B voters (between 0 and 1)",
)
@click.option(
    "--a-coh", type=float, required=True, help="Cohesion of A voters (between 0 and 1)"
)
@click.option(
    "--b-coh", type=float, required=True, help="Cohesion of B voters (between 0 and 1)"
)
def main(
    n_a_cand: int, n_b_cand: int, b_prop: float, a_coh: float, b_coh: float
) -> None:
    """Main function to execute the script.

    Args:
        n_a_cand (int): Number of A candidates.
        n_b_cand (int): Number of B candidates.
        b_prop (float): Proportion of B voters.
        a_coh (float): Cohesion of A voters.
        b_coh (float): Cohesion of B voters.
    """
    all_profiles = get_all_profiles(n_a_cand, n_b_cand, b_prop, a_coh, b_coh)

    with joblib_progress(total=len(all_profiles)):
        all_file_to_rule_dicts = Parallel(
            n_jobs=-1, prefer="processes", batch_size="auto"
        )(
            delayed(process_profile)(file, profile)
            for file, profile in all_profiles.items()
        )

    total_dictionary: dict[str, dict[str, float]] = {}
    for file_dict in all_file_to_rule_dicts:
        total_dictionary.update(file_dict)

    out_dir = Path(f"{TOP_DIR}/stats/bt_proportionality")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(
        f"{out_dir}/{n_a_cand:02d}_{n_b_cand:02d}_bprop_"
        f"{b_prop:0.1f}_cohesion_({a_coh:0.2f},{b_coh:0.2f})_results.json",
        "w",
    ) as f:
        json.dump(total_dictionary, f, indent=4)


if __name__ == "__main__":
    main()
