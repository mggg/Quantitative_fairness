from votekit import PreferenceProfile
from votekit.elections import *
from itertools import product
from glob import glob
from functools import partial
from fairness_metric import sigma_IIA, sigma_UM
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
import json
import contextlib
import warnings
from pathlib import Path
import os

warnings.filterwarnings("ignore")


def run_score(profile_file, metric_function, voting_rule):
    with contextlib.redirect_stdout(None):
        profile = PreferenceProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


if __name__ == "__main__":
    n_cand_list = [6, 7, 8, 9]
    alpha_list = [1 / 3, 1 / 2, 1, 2, 3]
    metric_list = ["sigma_IIA", "sigma_UM"]

    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of statistics are not overwritten.
    output_folder_base = str(Path("./bt_profile_stats_v2/").resolve())
    profile_folder_base = str(Path("./preference_profiles/").resolve())

    metric_function_dict = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
    }

    for n_cands, alpha, metric in product(n_cand_list, alpha_list, metric_list):
        election_name_to_class_dict = {
            "borda": partial(Borda, tiebreak="first_place"),
            "3-approval": partial(
                Borda,
                tiebreak="first_place",
                score_vector=[1] * 3 + [0] * (n_cands - 3),
            ),
            "2-approval": partial(
                Borda,
                tiebreak="first_place",
                score_vector=[1] * 2 + [0] * (n_cands - 2),
            ),
            "plurality": partial(Plurality, tiebreak="borda"),
            "stv": partial(STV, tiebreak="borda"),
        }

        all_csv_profiles = sorted(
            glob(f"{profile_folder_base}/{n_cands:02d}/alpha_{alpha:.2f}/*.csv")
        )
        for election_name, voting_rule in election_name_to_class_dict.items():
            with joblib_progress(
                f"{election_name}: n_cands = {n_cands:02d}, alpha = {alpha:.2f}, score = {metric}",
                total=len(all_csv_profiles),
            ):
                scores = Parallel(n_jobs=-1)(
                    delayed(run_score)(file, metric_function_dict[metric], voting_rule)
                    for file in all_csv_profiles
                )

            output_folder = (
                f"{output_folder_base}/{metric}/{n_cands:02d}/alpha_{alpha:.2f}/"
            )
            os.makedirs(output_folder, exist_ok=True)
            with open(
                f"{output_folder}/METRIC_{metric}__NCANDS_{n_cands}__ALPHA_{alpha:.2f}__TYPE_{election_name}.json",
                "w",
            ) as f:
                json.dump(scores, f)
