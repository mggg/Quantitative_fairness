from votekit import PreferenceProfile
from itertools import product
from glob import glob
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
import json
import contextlib
import warnings
from pathlib import Path
import os
import sys
from pathlib import Path
import click
from functools import partial

sys.path.append(str(Path(__file__).resolve().parents[2]))

from fairness_metric import (
    sigma_UM,
    sigma_UM_winner_set,
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
)
from voting_rules import build_voting_rule


warnings.filterwarnings("ignore")


def run_score(profile_file, metric_function, voting_rule):
    with contextlib.redirect_stdout(None):
        profile = PreferenceProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


@click.command()
@click.option("--n-seats", type=int, default=1, help="Number of seats")
@click.option("--n-cands", type=int, help="Number of candidates", required=True)
@click.option(
    "--alpha-value",
    type=click.Choice(["0.33", "0.50", "1.00", "2.00", "3.00"]),
    help="Alpha value",
    required=True,
)
@click.option(
    "--metric",
    type=click.Choice(
        [
            "sigma_UM",
            "sigma_UM_winner_set",
            "sigma_IIA",
            "sigma_IIA_all_subset",
            "sigma_IIA_winner_set",
        ]
    ),
    help="Metric to compute",
    required=True,
)
@click.option(
    "--variant",
    type=click.Choice(["worst_case", "average"]),
    help="Variant of the metric computation to use",
    required=True,
)
@click.option(
    "--interpolation-type",
    type=click.Choice(["asin", "odds", "None"]),
    help="Type of interpolation for sigma_UM metrics",
    default="asin",
    required=False,
)
@click.option(
    "--election-type",
    type=click.Choice(
        ["borda", "3-approval", "2-approval", "plurality", "stv", "ranked-pairs"]
    ),
    help="Type of election",
    required=True,
)
@click.option(
    "--tiebreak",
    type=click.Choice(["lex", "random"]),
    help="Tiebreaking method",
    required=True,
)
@click.option(
    "--show-progress",
    is_flag=True,
    help="Show progress bar",
    default=False,
)
def main(
    n_seats,
    n_cands,
    alpha_value,
    metric,
    variant,
    interpolation_type,
    election_type,
    tiebreak,
    show_progress,
):
    if n_seats < 1:
        raise ValueError("Number of seats must be at least 1.")

    alpha_dict = {
        "0.33": 1 / 3,
        "0.50": 1 / 2,
        "1.00": 1,
        "2.00": 2,
        "3.00": 3,
    }

    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(f"{top_dir}/stats/bt_profile_stats/{n_seats}_seats").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)
    profile_folder_base = str(Path(f"{top_dir}/data/preference_profiles/").resolve())

    if "UM" in metric:
        if interpolation_type not in ["asin", "odds"]:
            raise ValueError(
                f"Invalid interpolation type {interpolation_type} for metric {metric}. Must be 'asin' or 'odds'."
            )

    metric_function_dict = {
        "sigma_UM": partial(
            sigma_UM,
            n_seats=n_seats,
            variant=variant,
            interpolation_type=interpolation_type,
        ),
        "sigma_UM_winner_set": partial(
            sigma_UM_winner_set,
            n_seats=n_seats,
            variant=variant,
            interpolation_type=interpolation_type,
        ),
        "sigma_IIA": partial(sigma_IIA, n_seats=n_seats, variant=variant),
        "sigma_IIA_all_subset": partial(
            sigma_IIA_all_subset, n_seats=n_seats, variant=variant
        ),
        "sigma_IIA_winner_set": partial(
            sigma_IIA_winner_set, n_seats=n_seats, variant=variant
        ),
    }

    alpha = alpha_dict[alpha_value]
    all_csv_profiles = sorted(
        glob(f"{profile_folder_base}/{n_cands:02d}/alpha_{alpha:.2f}/*.csv")
    )
    voting_rule = build_voting_rule(n_cands, election_type, tiebreak=tiebreak)

    if show_progress:
        with joblib_progress(
            f"{n_seats} {n_cands} {metric} {variant} {interpolation_type} {election_type} {tiebreak} alpha {alpha:.2f}",
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

            output_file = f"{output_folder}/METRIC_{metric}__SEATS_{n_seats}__NCANDS_{n_cands}__ALPHA_{alpha:.2f}__TYPE_{election_type}__VARIANT_{variant}__TIEBREAK_{tiebreak}__INTERP_{interpolation_type}.json"
            with open(
                output_file,
                "w",
            ) as f:
                json.dump(scores, f)

    else:
        scores = Parallel(n_jobs=-1)(
            delayed(run_score)(file, metric_function_dict[metric], voting_rule)
            for file in all_csv_profiles
        )

        output_folder = (
            f"{output_folder_base}/{metric}/{n_cands:02d}/alpha_{alpha:.2f}/"
        )
        os.makedirs(output_folder, exist_ok=True)

        output_file = f"{output_folder}/METRIC_{metric}__SEATS_{n_seats}__NCANDS_{n_cands}__ALPHA_{alpha:.2f}__TYPE_{election_type}__VARIANT_{variant}__TIEBREAK_{tiebreak}__INTERP_{interpolation_type}.json"
        with open(
            output_file,
            "w",
        ) as f:
            json.dump(scores, f)


if __name__ == "__main__":
    main()
