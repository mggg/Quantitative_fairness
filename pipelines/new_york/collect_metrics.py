"""Collect New York mayoral election statistics across rules and metrics."""

import json
import sys
from pathlib import Path
from typing import Callable, cast

from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_winner_set,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.replication import DATA_DIR, STATS_OUTPUT, seed_task
from voting_metrics_main_code.voting_rules import (
    AllowedRule,
    build_voting_rule,
)


def score_profile(
    profile: RankProfile,
    election_name: AllowedRule,
    metric_functions: dict[str, Callable[..., float]],
) -> dict[str, list[float]]:
    """Compute the four primary metrics for one profile with independent metric seeds.

    Args:
        profile (RankProfile): Cleaned election profile.
        election_name (AllowedRule): Voting rule to evaluate.
        metric_functions (dict[str, Callable[..., float]]): Metrics in evaluation order.

    Returns:
        dict[str, list[float]]: Voter count and metric scores as singleton lists for JSON export.
    """
    voting_rule = build_voting_rule(len(profile.candidates), election_name)
    statistics = {
        "n_voters": [int(profile.df["Weight"].sum())],
        "sigma_UM": [],
        "sigma_IIA": [],
        "sigma_UM_winner_set": [],
        "sigma_IIA_winner_set": [],
    }

    for metric_name, metric_function in metric_functions.items():
        seed_task("ny", election_name, metric_name)
        score = float(metric_function(profile, voting_rule, n_seats=1))

        statistics[metric_name].append(score)

    return statistics


def main() -> None:
    """Save four primary metric scores for the New York mayoral profile under each rule."""
    output_folder = Path(f"{STATS_OUTPUT}/ny_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    metric_function_dict: dict[str, Callable[..., float]] = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
        "sigma_IIA_winner_set": sigma_IIA_winner_set,
        "sigma_UM_winner_set": sigma_UM_winner_set,
    }
    all_election_types: list[AllowedRule] = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
    ]

    for election_name in all_election_types:
        print(f"Processing {election_name} for NY Mayor")
        profile = RankProfile.from_csv(DATA_DIR / "NY_mayor_cleaned_votekit.csv")
        ny_election_stats = score_profile(
            cast(RankProfile, profile), election_name, metric_function_dict
        )

        output_file = f"{output_folder_base}/{election_name}_output.json"

        with open(output_file, "w") as f:
            json.dump(ny_election_stats, f, indent=4)


if __name__ == "__main__":
    main()
