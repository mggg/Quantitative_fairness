import json
from votekit import PreferenceProfile
from votekit.elections import STV, Plurality, Borda
from votekit.cvr_loaders import load_scottish
from glob import glob
from functools import partial
from fairness_metric import sigma_IIA, sigma_UM
import contextlib
from pathlib import Path
from tqdm import tqdm
import numpy as np


def run_score(profile_file, metric_function, voting_rule):
    with contextlib.redirect_stdout(None):
        profile = PreferenceProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


def build_voting_rule(n_cands, voting_rule_name):
    if voting_rule_name == "borda":
        return partial(Borda, tiebreak="first_place")
    elif voting_rule_name == "3-approval":
        return partial(
            Borda,
            tiebreak="first_place",
            score_vector=[1] * 3 + [0] * (n_cands - 3),
        )
    elif voting_rule_name == "2-approval":
        return partial(
            Borda,
            tiebreak="first_place",
            score_vector=[1] * 2 + [0] * (n_cands - 2),
        )
    elif voting_rule_name == "plurality":
        return partial(Plurality, tiebreak="borda")
    elif voting_rule_name == "stv":
        return partial(STV, tiebreak="borda")
    else:
        raise ValueError(f"Voting rule {voting_rule_name} not recognized.")


if __name__ == "__main__":
    n_cand_list = [6, 7, 8, 9]
    metric_list = ["sigma_IIA", "sigma_UM"]

    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of statistics are not overwritten.
    out_folder = Path("./scottish_stats_v2/").resolve()
    out_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(out_folder)

    metric_function_dict = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
    }

    all_files = glob("./scot-elex/*/*.csv")
    scottish_election_stats = {
        str(cands): {
            "n_voters": [],
            "sigma_UM": [],
            "sigma_IIA": [],
        }
        for cands in range(3, 15)
    }
    all_election_types = ["borda", "3-approval", "2-approval", "plurality", "stv"]

    for election_name in all_election_types:
        for f in tqdm(all_files[:]):
            n_cands = f.split("/")[-2].split("_")[0]
            voting_rule = build_voting_rule(int(n_cands), election_name)

            profile, _seats, _cand_list, _cand_to_party, _ward = load_scottish(f)
            scottish_election_stats[n_cands]["n_voters"].append(
                int(profile.df["Weight"].sum())
            )
            scottish_election_stats[n_cands]["sigma_UM"].append(
                float(sigma_UM(profile, voting_rule))
            )
            scottish_election_stats[n_cands]["sigma_IIA"].append(
                float(sigma_IIA(profile, voting_rule))
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
            scottish_election_interpreted_values[key]["mean_sigma_IIA"] = float(
                np.mean(data["sigma_IIA"])
            )
            scottish_election_interpreted_values[key]["variance_sigma_IIA"] = float(
                np.var(data["sigma_IIA"])
            )
            scottish_election_interpreted_values[key]["mean_sigma_UM"] = float(
                np.mean(data["sigma_UM"])
            )
            scottish_election_interpreted_values[key]["variance_sigma_UM"] = float(
                np.var(data["sigma_UM"])
            )

        stats_file = f"{output_folder_base}/{election_name}_stats.json"
        with open(stats_file, "w") as f:
            json.dump(scottish_election_interpreted_values, f, indent=4)
