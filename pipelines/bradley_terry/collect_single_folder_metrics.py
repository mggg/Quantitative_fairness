"""Collect one metric from a single two-bloc BT profile folder using the historical CLI."""

import ast
import contextlib
import json
import os
import sys
import warnings
from glob import glob
from pathlib import Path

import click
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry._metrics import configure_metric

from voting_metrics_main_code.replication import STATS_OUTPUT
from voting_metrics_main_code.voting_rules import build_voting_rule

warnings.filterwarnings("ignore")


def run_score(profile_file, metric_function, voting_rule):
    """Load one profile and evaluate its metric with standard output suppressed.

    Args:
        profile_file (str | Path): Path to a preference-profile CSV.
        metric_function (Callable[..., float]): Metric callable with seat count and variants already
            bound.
        voting_rule (ElectionConstructor): Voting rule callable passed to the metric.

    Returns:
        float: Metric score for the loaded profile.

    Raises:
        FileNotFoundError: The profile CSV does not exist.
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
    type=click.Choice(
        ["borda", "plurality", "stv", "2-approval", "3-approval", "ranked-pairs", "random"]
    ),
    help="Type of election",
    required=True,
)
@click.option(
    "--tiebreak",
    type=click.Choice(["random", "lex"]),
    help="Tiebreaking method",
    default="lex",
)
def main(
    input_folder,
    n_seats,
    metric,
    variant,
    interpolation_type,
    election_type,
    tiebreak,
):
    """Collect and save one metric for a two-bloc profile folder.

    Args:
        input_folder (str | Path): Two-bloc profile directory with encoded candidate and bloc
            parameters.
        n_seats (int): Number of seats to elect.
        metric (str): Metric identifier used in the statistics filenames.
        variant (str): Metric aggregation variant, 'average' or 'worst_case'.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
        election_type (str): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.

    Raises:
        ValueError: The seat count is below one or a UM interpolation is not 'asin', 'odds', or
            'linear'.
    """
    input_folder_full_path = Path(input_folder).resolve()
    base_parent = input_folder_full_path.name
    cand_folder = input_folder_full_path.parent.stem

    base_parts = base_parent.split("__")
    cand_parts = cand_folder.split("_")

    b_proportion = float(base_parts[0].split("_")[-1])
    aa_alpha, ab_alpha, ba_alpha, bb_alpha = ast.literal_eval(base_parts[1].split("_")[-1])
    a_cohesion, b_cohesion = ast.literal_eval(base_parts[2].split("_")[-1])
    n_a_cands = int(cand_parts[0])
    n_b_cands = int(cand_parts[1])

    if n_seats < 1:
        raise ValueError("Number of seats must be at least 1.")

    output_folder = Path(f"{STATS_OUTPUT}/bt_2_bloc_profile_stats/{n_seats}_seats").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    if "UM" in metric:
        if interpolation_type not in ["asin", "odds", "linear"]:
            raise ValueError(
                f"Invalid interpolation type {interpolation_type} for metric {metric}. Must"
                f" be 'asin' or 'odds'."
            )

    n_cands = n_a_cands + n_b_cands

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

    metric_function = configure_metric(metric, n_seats, variant, interpolation_type)

    all_csv_profiles = sorted(glob(f"{input_folder_full_path}/*.csv"))

    voting_rule = build_voting_rule(n_cands, election_type, tiebreak=tiebreak)

    scores = []

    with joblib_progress(
        description=f"Computing scores for metric {metric}", total=len(all_csv_profiles)
    ):
        scores = Parallel(n_jobs=-1)(
            delayed(run_score)(file, metric_function, voting_rule) for file in all_csv_profiles
        )

    with open(output_file, "w") as f:
        json.dump(scores, f)


if __name__ == "__main__":
    main()
