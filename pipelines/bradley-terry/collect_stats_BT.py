"""Collect BT profile statistics across metrics and voting rules."""

import ast
import contextlib
from functools import partial
from glob import glob
import json
import os
from pathlib import Path
import sys
from typing import Callable
import warnings
from typing import cast

import click
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile

sys.path.append(str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.fairness_metric import (
    sigma_UM,
    sigma_UM_winner_set,
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_all_subset,
)
from voting_metrics_main_code.voting_rules import AllowedRule, build_voting_rule


warnings.filterwarnings("ignore")


MetricFn = Callable[..., float]


def run_score(
    profile_file: str | Path,
    metric_function: MetricFn,
    voting_rule: object,
) -> float:
    """Compute a metric score for a single profile file.

    Args:
        profile_file (str | Path): Path to the profile CSV.
        metric_function (MetricFn): Metric function to evaluate.
        voting_rule (object): Voting rule callable.

    Returns:
        float: The computed metric score.
    """
    with contextlib.redirect_stdout(None):
        profile = RankProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)
    return score


@click.command()
@click.option(
    "--input-folder",
    type=str,
    required=True,
)
@click.option("--n-seats", type=int, default=1, help="Number of seats")
@click.option(
    "--metric",
    type=click.Choice(
        [
            "sigma_UM",
            "sigma_UM_winner_set",
            "sigma_IIA",
            "sigma_IIA_all_subset",
            "sigma_IIA_winner_set",
            "sigma_IIA_winner_set_all_subset",
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
    type=click.Choice(["asin", "odds", "linear", "None"]),
    help="Type of interpolation for sigma_UM metrics",
    default="asin",
    required=False,
)
@click.option(
    "--election-type",
    type=click.Choice(["borda", "plurality", "stv"]),
    help="Type of election",
    required=True,
)
def main(
    input_folder: str,
    n_seats: int,
    metric: str,
    variant: str,
    interpolation_type: str,
    election_type: str,
) -> None:
    """Run the BT metrics pipeline for a single input folder.

    Args:
        input_folder (str): Folder containing profile CSVs.
        n_seats (int): Number of seats to elect.
        metric (str): Metric name to compute.
        variant (str): Variant of the metric computation.
        interpolation_type (str): Interpolation type for UM metrics.
        election_type (str): Voting rule name.
    """
    input_folder_full_path = Path(input_folder).resolve()
    base_parent = input_folder_full_path.name
    cand_folder = input_folder_full_path.parent.stem

    base_parts = base_parent.split("__")
    cand_parts = cand_folder.split("_")

    b_proportion = float(base_parts[0].split("_")[-1])
    aa_alpha, ab_alpha, ba_alpha, bb_alpha = ast.literal_eval(
        base_parts[1].split("_")[-1]
    )
    a_cohesion, b_cohesion = ast.literal_eval(base_parts[2].split("_")[-1])
    n_a_cands = int(cand_parts[0])
    n_b_cands = int(cand_parts[1])

    if n_seats < 1:
        raise ValueError("Number of seats must be at least 1.")

    top_dir = str(Path(__file__).resolve().parents[2])
    output_folder = Path(
        f"{top_dir}/stats/bt_2_bloc_profile_stats/{n_seats}_seats"
    ).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    if "UM" in metric:
        if interpolation_type not in ["asin", "odds", "linear"]:
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
        "sigma_IIA_winner_set_all_subset": partial(
            sigma_IIA_winner_set_all_subset, n_seats=n_seats, variant=variant
        ),
    }

    n_cands = n_a_cands + n_b_cands
    tiebreak = "random"

    output_folder = f"{output_folder_base}/{metric}/{n_cands:02d}/{election_type}/"
    file_basename = (
        f"METRIC_{metric}"
        f"__VARIANT_{variant}"
        f"__INTERP_{interpolation_type}"
        f"__NCANDS_({n_a_cands:02d}_{n_b_cands:02d})"
        f"__SEATS_{n_seats}"
        f"__BPROP_{b_proportion:0.1f}"
        f"__ALPHA_({aa_alpha:0.2f},{ab_alpha:0.2f},{ba_alpha:0.2f},{bb_alpha:0.2f})"
        f"__COHESION_({a_cohesion:0.2f},{b_cohesion:0.2f})"
        f"__TYPE_{election_type}"
        f"__TIEBREAK_{tiebreak}"
    )
    os.makedirs(output_folder, exist_ok=True)
    output_file = f"{output_folder}/{file_basename}.json"

    if os.path.exists(output_file):
        print(f"Output file {output_file} already exists. Skipping computation.")
        return

    all_csv_profiles = sorted(glob(f"{input_folder_full_path}/*.csv"))

    voting_rule = build_voting_rule(
        n_cands, cast(AllowedRule, election_type), tiebreak=tiebreak
    )

    with joblib_progress(
        description=f"Computing scores for metric {metric}", total=len(all_csv_profiles)
    ):
        scores = Parallel(n_jobs=-1)(
            delayed(run_score)(file, metric_function_dict[metric], voting_rule)
            for file in all_csv_profiles
        )

    with open(output_file, "w") as f:
        json.dump(scores, f)


if __name__ == "__main__":
    main()
