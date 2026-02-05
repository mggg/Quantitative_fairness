"""Collect New York mayoral election statistics across rules and metrics."""

from typing import Callable, cast

from votekit import RankProfile
import json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_UM,
    sigma_IIA_winner_set,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.voting_rules import AllowedRule, ElectionConstructor, build_voting_rule


if __name__ == "__main__":
    # Load the data
    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/ny_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    base_data_dir = str(Path(f"{top_dir}/data").resolve())

    n_seats = 1

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
        ny_election_stats = {
            "n_voters": [],
            "sigma_UM": [],
            "sigma_IIA": [],
            "sigma_UM_winner_set": [],
            "sigma_IIA_winner_set": [],
        }

        clean_profile = RankProfile.from_csv(
            f"{base_data_dir}/NY_mayor_cleaned_votekit.csv"
        )
        voting_rule: ElectionConstructor = build_voting_rule(
            len(clean_profile.candidates), election_name
        )
        ny_election_stats["n_voters"].append(int(clean_profile.df["Weight"].sum()))

        for metric_name, metric_function in metric_function_dict.items():
            ny_election_stats[metric_name].append(
                float(
                    metric_function(
                        cast(RankProfile, clean_profile),
                        voting_rule,
                        n_seats=n_seats,
                    )
                )
            )

        output_file = f"{output_folder_base}/{election_name}_output.json"
        with open(output_file, "w") as f:
            json.dump(ny_election_stats, f, indent=4)
