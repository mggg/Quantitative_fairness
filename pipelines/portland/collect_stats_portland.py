from votekit import PreferenceProfile
from functools import partial
from votekit.elections import Borda, STV, Plurality
import json

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from fairness_metric import (
    sigma_IIA,
    sigma_UM,
    sigma_IIA_winner_set,
    sigma_UM_winner_set,
)
from voting_rules import build_voting_rule


if __name__ == "__main__":
    # Load the data
    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/portland_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    base_data_dir = str(Path(f"{top_dir}/data").resolve())

    n_seats = 3

    districts = ["D1", "D2", "D3", "D4"]
    metric_function_dict = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
        "sigma_IIA_winner_set": sigma_IIA_winner_set,
        "sigma_UM_winner_set": sigma_UM_winner_set,
    }
    all_election_types = ["borda", "3-approval", "2-approval", "plurality", "stv"]

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
            clean_profile = PreferenceProfile.from_csv(
                f"{base_data_dir}/Portland_{district}_cleaned_votekit.csv"
            )
            voting_rule = build_voting_rule(
                len(clean_profile.candidates), election_name
            )
            portland_election_stats[district]["n_voters"].append(
                int(clean_profile.df["Weight"].sum())
            )

            for metric_name, metric_function in metric_function_dict.items():
                portland_election_stats[district][metric_name].append(
                    float(metric_function(clean_profile, voting_rule, n_seats=n_seats))
                )

        output_file = f"{output_folder_base}/{election_name}_output.json"
        with open(output_file, "w") as f:
            json.dump(portland_election_stats, f, indent=4)
