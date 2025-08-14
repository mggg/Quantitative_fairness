import json
from votekit import PreferenceProfile
from votekit.elections import STV, Plurality, Borda
from votekit.cvr_loaders import load_scottish
from glob import glob
from functools import partial
import contextlib
from pathlib import Path
from tqdm import tqdm
import numpy as np
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from fairness_metric import (
    sigma_IIA,
    sigma_UM,
    sigma_IIA_winner_set,
    sigma_UM_winner_set,
)
from voting_rules import build_voting_rule


def run_score(profile_file, metric_function, voting_rule):
    with contextlib.redirect_stdout(None):
        profile = PreferenceProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


if __name__ == "__main__":
    n_cand_list = [6, 7, 8, 9]

    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of statistics are not overwritten.
    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/scottish_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    all_files = glob(f"{top_dir}/data/scot-elex/*/*.csv")

    metric_function_dict = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
        "sigma_IIA_winner_set": sigma_IIA_winner_set,
        "sigma_UM_winner_set": sigma_UM_winner_set,
    }
    all_election_types = ["borda", "3-approval", "2-approval", "plurality", "stv"]

    for election_name in all_election_types:
        scottish_election_stats = {
            str(cands): {
                "n_voters": [],
                "sigma_UM": [],
                "sigma_IIA": [],
                "sigma_UM_winner_set": [],
                "sigma_IIA_winner_set": [],
            }
            for cands in range(3, 15)
        }

        for f in tqdm(all_files[:]):
            profile, seats, _cand_list, _cand_to_party, _ward = load_scottish(f)

            n_cands = f.split("/")[-2].split("_")[0]
            voting_rule = build_voting_rule(int(n_cands), election_name)

            scottish_election_stats[n_cands]["n_voters"].append(
                int(profile.df["Weight"].sum())
            )
            for metric_name, metric_function in metric_function_dict.items():
                scottish_election_stats[n_cands][metric_name].append(
                    float(metric_function(profile, voting_rule, n_seats=seats))
                )

        # Save the full output
        output_file = f"{output_folder_base}/{election_name}_output.json"
        with open(output_file, "w") as f:
            json.dump(scottish_election_stats, f, indent=4)

        # Now for the stats we care about
        scottish_election_interpreted_values = {
            str(cands): {} for cands in range(3, 15)
        }

        for key, data in scottish_election_stats.items():
            scottish_election_interpreted_values[key]["median_voters"] = int(
                np.median(data["n_voters"])
            )
            scottish_election_interpreted_values[key]["max_voters"] = int(
                np.max(data["n_voters"])
            )

            for metric_name in metric_function_dict.keys():
                scottish_election_interpreted_values[key][f"mean_{metric_name}"] = (
                    float(np.mean(data[metric_name]))
                )
                scottish_election_interpreted_values[key][f"variance_{metric_name}"] = (
                    float(np.var(data[metric_name]))
                )

        stats_file = f"{output_folder_base}/{election_name}_stats.json"
        with open(stats_file, "w") as f:
            json.dump(scottish_election_interpreted_values, f, indent=4)
