"""Collect Portland election statistics across rules and metrics."""

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
    ElectionConstructor,
    build_voting_rule,
)


def main() -> None:
    output_folder = Path(f"{STATS_OUTPUT}/portland_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    base_data_dir = str(DATA_DIR)

    n_seats = 3

    districts = ["D1", "D2", "D3", "D4"]
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
        portland_election_stats = {
            district: {
                "n_voters": [],
                "sigma_UM": [],
                "sigma_IIA": [],
                "sigma_UM_winner_set": [],
                "sigma_IIA_winner_set": [],
            }
            for district in districts
        }

        for district in districts:
            print(f"Processing {election_name} for {district}")
            clean_profile = RankProfile.from_csv(
                f"{base_data_dir}/Portland_{district}_cleaned_votekit.csv"
            )
            voting_rule: ElectionConstructor = build_voting_rule(
                len(clean_profile.candidates), election_name
            )
            portland_election_stats[district]["n_voters"].append(
                int(clean_profile.df["Weight"].sum())
            )

            for metric_name, metric_function in metric_function_dict.items():
                seed_task("portland", district, election_name, metric_name)
                portland_election_stats[district][metric_name].append(
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
            json.dump(portland_election_stats, f, indent=4)


if __name__ == "__main__":
    main()
