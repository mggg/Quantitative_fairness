import json
from votekit import PreferenceProfile
from votekit.cvr_loaders import load_scottish
from glob import glob
import contextlib
from pathlib import Path
import numpy as np
import pandas as pd
import sys
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from itertools import product

sys.path.append(str(Path(__file__).resolve().parents[2]))

from fairness_metric import (
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_rules import build_voting_rule


def run_score(profile_file, metric_function, voting_rule):
    with contextlib.redirect_stdout(None):
        profile = PreferenceProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


def compute_results_single_file(f, election_name, metric_function_dict, tiebreak):
    file_name = str(Path(f).stem)

    output = load_scottish(f)
    profile, seats = output[:2]

    n_cands = f.split("/")[-2].split("_")[0]
    voting_rule = build_voting_rule(int(n_cands), election_name, tiebreak=tiebreak)

    output_dict = {
        f"{metric_name}_{tiebreak}": {} for metric_name in metric_function_dict.keys()
    }

    for metric_name, metric_function in metric_function_dict.items():
        output_dict[f"{metric_name}_{tiebreak}"][file_name] = float(
            metric_function(profile, voting_rule, n_seats=seats)
        )
    return {n_cands: output_dict}


# =================================================================


def sigma_UM_worst_case_asin():

    def wrapper(*args, **kwargs):
        return sigma_UM(
            *args, variant="worst_case", interpolation_type="asin", **kwargs
        )

    return wrapper


def sigma_UM_average_asin():
    def wrapper(*args, **kwargs):
        return sigma_UM(*args, variant="average", interpolation_type="asin", **kwargs)

    return wrapper


def sigma_UM_worst_case_odds():
    def wrapper(*args, **kwargs):
        return sigma_UM(
            *args, variant="worst_case", interpolation_type="odds", **kwargs
        )

    return wrapper


def sigma_UM_average_odds():
    def wrapper(*args, **kwargs):
        return sigma_UM(*args, variant="average", interpolation_type="odds", **kwargs)

    return wrapper


def sigma_UM_winner_set_worst_case_asin():
    def wrapper(*args, **kwargs):
        return sigma_UM_winner_set(
            *args, variant="worst_case", interpolation_type="asin", **kwargs
        )

    return wrapper


def sigma_UM_winner_set_average_asin():
    def wrapper(*args, **kwargs):
        return sigma_UM_winner_set(
            *args, variant="average", interpolation_type="asin", **kwargs
        )

    return wrapper


def sigma_UM_winner_set_worst_case_odds():
    def wrapper(*args, **kwargs):
        return sigma_UM_winner_set(
            *args, variant="worst_case", interpolation_type="odds", **kwargs
        )

    return wrapper


def sigma_UM_winner_set_average_odds():
    def wrapper(*args, **kwargs):
        return sigma_UM_winner_set(
            *args, variant="average", interpolation_type="odds", **kwargs
        )

    return wrapper


# =================================================================


def sigma_IIA_worst_case():
    def wrapper(*args, **kwargs):
        return sigma_IIA(*args, variant="worst_case", **kwargs)

    return wrapper


def sigma_IIA_average():
    def wrapper(*args, **kwargs):
        return sigma_IIA(*args, variant="average", **kwargs)

    return wrapper


def sigma_IIA_all_subset_worst_case():
    def wrapper(*args, **kwargs):
        return sigma_IIA_all_subset(*args, variant="worst_case", **kwargs)

    return wrapper


def sigma_IIA_all_subset_average():
    def wrapper(*args, **kwargs):
        return sigma_IIA_all_subset(*args, variant="average", **kwargs)

    return wrapper


def sigma_IIA_winner_set_worst_case():
    def wrapper(*args, **kwargs):
        return sigma_IIA_winner_set(*args, variant="worst_case", **kwargs)

    return wrapper


def sigma_IIA_winner_set_average():
    def wrapper(*args, **kwargs):
        return sigma_IIA_winner_set(*args, variant="average", **kwargs)

    return wrapper


if __name__ == "__main__":
    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of statistics are not overwritten.
    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/scottish_stats/").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    # WARN: Change this for different candidate ranges
    candidate_range = range(3, 10)

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
    }
    all_election_types = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
    ]
    tiebreak_types = ["lex", "random"]
    file_to_column_data_dict = {}

    for f in all_files[:]:
        file_name = str(Path(f).stem)
        file_to_column_data_dict[file_name] = dict()

    for election_name in all_election_types:
        scottish_election_stats = {
            str(cands): {
                f"{metric_name}_{tiebreak}": {}
                for metric_name, tiebreak in product(
                    metric_function_dict.keys(), tiebreak_types
                )
            }
            for cands in candidate_range
        }
        for tiebreak in tiebreak_types:

            with joblib_progress(
                total=len(all_files),
                description=f"Collecting stats for {election_name}, tiebreak={tiebreak}",
            ):
                results = Parallel(n_jobs=28)(
                    delayed(compute_results_single_file)(
                        f, election_name, metric_function_dict, tiebreak
                    )
                    for f in all_files
                )

            for output_dict in results:
                assert output_dict is not None
                for n_cands, data in output_dict.items():
                    for key, value_dict in data.items():
                        scottish_election_stats[n_cands][key].update(value_dict)

        # Save the full output
        output_file = f"{output_folder_base}/{election_name}_output.json"
        with open(output_file, "w") as f:
            json.dump(scottish_election_stats, f, indent=4)

        # Now for the stats we care about
        scottish_election_interpreted_values = {
            str(cands): {} for cands in candidate_range
        }

        from pprint import pprint

        for key, data_dict in scottish_election_stats.items():
            if data_dict == {
                f"{metric}_{tiebreak}": {}
                for metric, tiebreak in product(
                    metric_function_dict.keys(), tiebreak_types
                )
            }:
                print(f"No data for {key}, skipping.")
                continue

            for metric_name, tiebreak in product(
                metric_function_dict.keys(), tiebreak_types
            ):
                pprint(data_dict)
                metric_data_list = list(data_dict[f"{metric_name}_{tiebreak}"].values())
                scottish_election_interpreted_values[key][
                    f"mean_{metric_name}_{tiebreak}"
                ] = float(np.mean(metric_data_list))
                scottish_election_interpreted_values[key][
                    f"variance_{metric_name}_{tiebreak}"
                ] = float(np.var(metric_data_list))

        stats_file = f"{output_folder_base}/{election_name}_stats.json"
        with open(stats_file, "w") as f:
            json.dump(scottish_election_interpreted_values, f, indent=4)

        for f in all_files:
            file_name = str(Path(f).stem)
            n_cands = f.split("/")[-2].split("_")[0]

            data = {
                "n_cands": n_cands,
            } | {
                metric: scottish_election_stats[n_cands][f"{metric}_{tiebreak}"][
                    file_name
                ]
                for metric, tiebreak in product(
                    metric_function_dict.keys(), tiebreak_types
                )
            }

            file_to_column_data_dict[file_name][election_name] = data

    df = pd.concat(
        {
            file_name: pd.DataFrame(methods_dict).T
            for file_name, methods_dict in file_to_column_data_dict.items()
        }
    )

    # Move ward and method into columns instead of MultiIndex
    df.index.names = ["election_name", "method"]
    df = df.reset_index()
    df.to_csv(
        f"{output_folder_base}/scottish_stats_tagged_by_election.csv", index=False
    )
