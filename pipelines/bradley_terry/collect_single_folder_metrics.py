"""Collect one metric from a single two-bloc BT profile folder using the historical CLI."""

import ast
import contextlib
import json
import sys
from collections.abc import Callable
from pathlib import Path

import click
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry._metrics import configure_metric, parse_metric_spec
from voting_metrics_main_code.constants import AllowedRule, MetricVariant
from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import ElectionConstructor, build_voting_rule


def run_score(
    profile_file: str | Path,
    metric_function: Callable[..., float],
    voting_rule: ElectionConstructor,
    *,
    seed: int = 0,
) -> float:
    """Load one profile and evaluate its metric with standard output suppressed.

    Args:
        profile_file (str | Path): Path to a preference-profile CSV.
        metric_function (Callable[..., float]): Metric callable with seat count and variants already
            bound.
        voting_rule (ElectionConstructor): Voting rule callable passed to the metric.
        seed (int, optional): Base seed for independent profile streams. Defaults to 0.

    Returns:
        float: Metric score for the loaded profile.

    Raises:
        FileNotFoundError: The profile CSV does not exist.
    """
    profile_path = Path(profile_file)
    seed_task(
        profile_path.parent.parent.name, profile_path.parent.name, profile_path.name, seed=seed
    )
    with contextlib.redirect_stdout(None):
        profile = RankProfile.from_csv(profile_file)
        score = metric_function(profile, voting_rule)

    return score


def build_output_path(
    input_folder: str | Path,
    n_seats: int,
    metric: str,
    variant: MetricVariant,
    interpolation_type: str,
    election_type: AllowedRule,
    tiebreak: str,
    output_root: Path,
) -> tuple[int, Path]:
    """Parse a BT profile folder and build its historical metric output path without writing.

    Args:
        input_folder (str | Path): Profile directory with encoded candidate and bloc parameters.
        n_seats (int): Seat count encoded in the statistics path.
        metric (str): Metric identifier encoded in the directory and filename.
        variant (MetricVariant): Aggregation variant encoded in the filename.
        interpolation_type (str): Historical interpolation token, including 'None' for IIA.
        election_type (AllowedRule): Voting rule encoded in the directory and filename.
        tiebreak (str): Tie-breaking token encoded in the filename.
        output_root (Path): Run root containing the statistics tree.

    Returns:
        tuple[int, Path]: Total candidate count and the corresponding metric output path.

    Raises:
        ValueError: Encoded candidate counts or bloc parameters cannot be parsed or unpacked.
        IndexError: The directory name lacks a required parameter segment.
        SyntaxError: An encoded alpha or cohesion tuple is not a valid Python literal.
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

    n_cands = n_a_cands + n_b_cands

    output_folder = (
        output_root
        / "stats/bt_2_bloc_profile_stats"
        / f"{n_seats}_seats"
        / metric
        / f"{n_cands:02d}"
        / election_type
    )
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
    return n_cands, output_folder / f"{file_basename}.json"


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
@click.option(
    "--output-dir",
    "output_root",
    type=click.Path(path_type=Path),
    default=ROOT,
    show_default=True,
    help="Run root containing stats, plots, and tables",
)
@click.option("--n-jobs", type=click.IntRange(min=1), default=1, show_default=True)
@click.option("--seed", type=int, default=0, show_default=True)
def main(
    input_folder: str | Path,
    n_seats: int,
    metric: str,
    variant: MetricVariant,
    interpolation_type: str,
    election_type: AllowedRule,
    tiebreak: str,
    *,
    output_root: Path = ROOT,
    n_jobs: int = 1,
    seed: int = 0,
) -> None:
    """Collect and save one metric for a two-bloc profile folder.

    Args:
        input_folder (str | Path): Two-bloc profile directory with encoded candidate and bloc
            parameters.
        n_seats (int): Number of seats to elect.
        metric (str): Metric identifier used in the statistics filenames.
        variant (MetricVariant): Metric aggregation variant, 'average' or 'worst_case'.
        interpolation_type (str): UM interpolation token; use the string 'None' for IIA metrics.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_jobs (int, optional): Number of parallel workers. Defaults to 1.
        seed (int, optional): Base seed for independent profile streams. Defaults to 0.

    Raises:
        ValueError: The seat count is below one or a UM interpolation is not 'asin', 'odds', or
            'linear'.
    """
    output_root = output_root.resolve()
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    if n_seats < 1:
        raise ValueError("Number of seats must be at least 1.")
    spec = parse_metric_spec(metric, variant, interpolation_type)
    n_cands, output_file = build_output_path(
        input_folder,
        n_seats,
        metric,
        variant,
        interpolation_type,
        election_type,
        tiebreak,
        output_root,
    )
    if output_file.exists() or output_file.is_symlink():
        print(f"Skipping existing result: {output_file}. Move it manually to recompute.")

        return

    metric_function = configure_metric(spec, n_seats)

    all_csv_profiles = sorted(Path(input_folder).resolve().glob("*.csv"))

    voting_rule = build_voting_rule(n_cands, election_type, tiebreak=tiebreak)

    scores = []

    with joblib_progress(
        description=f"Computing scores for metric {metric}", total=len(all_csv_profiles)
    ):
        scores = Parallel(n_jobs=n_jobs)(
            delayed(run_score)(file, metric_function, voting_rule, seed=seed)
            for file in all_csv_profiles
        )

    with new_data_file(output_file) as temporary, temporary.open("w") as f:
        json.dump(scores, f)


if __name__ == "__main__":
    main()
