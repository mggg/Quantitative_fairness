"""Compute proportionality diagnostics for BT preference profiles."""

import json
import sys
from glob import escape, glob
from pathlib import Path
from typing import cast, get_args

import click
import pandas as pd
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import RankProfile
from votekit.ballot_generator import BlocSlateConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import AllowedRule, build_voting_rule


def load_profile(path: str) -> tuple[str, RankProfile]:
    """Load a preference profile from a CSV file.

    Args:
        path (str): The path to the CSV file.

    Returns:
        tuple[str, RankProfile]: A tuple containing the file path and the loaded
            RankProfile.
    """
    return path, cast(RankProfile, RankProfile.from_csv(path))


def load_profiles(
    n_a_cand: int,
    n_b_cand: int,
    b_prop: float,
    a_coh: float,
    b_coh: float,
    *,
    data_root: Path,
    n_jobs: int = 1,
) -> dict[str, RankProfile]:
    """Load the profiles matching the selected candidate counts and bloc parameters.

    Args:
        n_a_cand (int): Number of A candidates.
        n_b_cand (int): Number of B candidates.
        b_prop (float): Proportion of B voters.
        a_coh (float): Cohesion of A voters.
        b_coh (float): Cohesion of B voters.
        data_root (Path): Directory containing election inputs.
        n_jobs (int, optional): Number of parallel workers. Defaults to 1.

    Returns:
        dict[str, RankProfile]: A dictionary mapping file paths to RankProfiles.
    """
    search_string = (
        f"{escape(str(data_root))}/preference_profiles/{n_a_cand:02d}_{n_b_cand:02d}/"
        f"b_proportion_{b_prop:0.1f}__ALPHA_(*)__COHESION_({a_coh:0.2f},{b_coh:0.2f})/*.csv"
    )
    profile_files = sorted(glob(search_string))

    with joblib_progress(total=len(profile_files)):
        # Joblib's default list result contains exactly the worker return values.
        pairs = cast(
            list[tuple[str, RankProfile]],
            Parallel(n_jobs=n_jobs, prefer="processes", batch_size="auto")(
                delayed(load_profile)(p) for p in profile_files
            ),
        )

    all_profiles = dict(pairs)

    return all_profiles


def compute_slate_first_probability(r: int, s: int, rho: float) -> float:
    """Calculate the probability of one slate putting another slate first.

    Args:
        r (int): Number of candidates in the first slate.
        s (int): Number of candidates in the second slate.
        rho (float): Cohesion parameter.

    Returns:
        float: The calculated probability.
    """
    return 1 - (1 - rho**s) / (1 - rho ** (r + s))


def load_profile_config(profile_path: Path) -> BlocSlateConfig:
    """Load and validate the utility table and two-bloc parameters paired with a profile.

    Args:
        profile_path (Path): Profile CSV beneath the two-bloc preference_profiles directory tree.

    Returns:
        BlocSlateConfig: Voter counts, bloc parameters, and normalized intervals from paired inputs.

    Raises:
        FileNotFoundError: The profile CSV or its paired utility CSV is missing.
        ValueError: Encoded parameters or the loaded configuration are invalid.
        IndexError: The path lacks a required directory or parameter segment.
    """
    relative_profile = profile_path.relative_to(profile_path.parents[2])
    utility_file = (
        profile_path.parents[3]
        / "preference_dfs"
        / relative_profile.with_name(f"{profile_path.stem}_utilities.csv")
    )
    utility_df = pd.read_csv(utility_file, index_col=0)
    ranking_df = pd.read_csv(profile_path, skiprows=list(range(8)))

    a_cohesion, b_cohesion = list(
        map(float, profile_path.parent.name.split("_COHESION_(")[1].split(")")[0].split(","))
    )
    b_proportion = float(profile_path.parent.name.split("b_proportion_")[1].split("__")[0])

    n_a_candidates, n_b_candidates = list(map(int, profile_path.parent.parent.name.split("_")))
    slate_to_candidates = {
        "bloc_1": [f"A{i}" for i in range(1, n_a_candidates + 1)],
        "bloc_2": [f"B{j}" for j in range(1, n_b_candidates + 1)],
    }

    n_voters = int(ranking_df["Weight"].sum())

    config = BlocSlateConfig(
        n_voters=n_voters,
        slate_to_candidates=slate_to_candidates,
        cohesion_mapping={
            "bloc_1": {"bloc_1": a_cohesion, "bloc_2": 1 - a_cohesion},
            "bloc_2": {"bloc_1": 1 - b_cohesion, "bloc_2": b_cohesion},
        },
        bloc_proportions={"bloc_1": 1 - b_proportion, "bloc_2": b_proportion},
        preference_mapping=utility_df,
    )
    config.normalize_preference_intervals()
    return config


def compute_expected_b_proportion(config: BlocSlateConfig) -> float:
    """Compute expected B representation, retaining integer truncation of the B voter count.

    Args:
        config (BlocSlateConfig): Two-bloc configuration with bloc_1 representing A and bloc_2 B.

    Returns:
        float: Expected fraction of first-place votes for B, used as expected representation.

    Raises:
        KeyError: A required bloc, slate, or cohesion entry is absent.
        ZeroDivisionError: A cohesion-derived denominator or total voter count is zero.
    """
    n_voters = config.n_voters
    b_proportion = config.bloc_proportions["bloc_2"]
    a_cohesion = float(cast(float, config.cohesion_df.loc["bloc_1", "bloc_1"]))
    b_cohesion = float(cast(float, config.cohesion_df.loc["bloc_2", "bloc_2"]))
    n_b_voters = int(b_proportion * n_voters)
    n_a_voters = n_voters - n_b_voters
    n_a_candidates = len(config.slate_to_candidates["bloc_1"])
    n_b_candidates = len(config.slate_to_candidates["bloc_2"])

    prob_b_puts_b_first = compute_slate_first_probability(
        n_b_candidates, n_a_candidates, b_cohesion / (1 - b_cohesion)
    )
    prob_a_puts_a_first = compute_slate_first_probability(
        n_a_candidates, n_b_candidates, a_cohesion / (1 - a_cohesion)
    )

    expected_b_fpv = n_b_voters * prob_b_puts_b_first + n_a_voters * (1 - prob_a_puts_a_first)
    return expected_b_fpv / n_voters


def collect_profile_proportionality(
    file: str, profile: RankProfile, *, seed: int = 0
) -> dict[str, dict[str, dict[str, float]]]:
    """Load paired utilities and compare expected B representation with each rule's winners.

    Returns the historical file-to-rule mapping for JSON export. Each profile receives an
    independent seed before evaluating rules in the shared rule order.

    Args:
        file (str): Profile CSV path used to locate paired utilities and identify exported results.
        profile (RankProfile): Loaded profile for evaluating three-seat elections.
        seed (int, optional): Base seed for the profile's rule evaluations. Defaults to 0.

    Returns:
        dict[str, dict[str, dict[str, float]]]: Profile path mapped to each rule's expected and
            observed B representation.

    Raises:
        FileNotFoundError: A required profile or utility CSV is missing.
        ValueError: The configuration or a voting rule rejects the election inputs.
        ZeroDivisionError: A cohesion-derived denominator, voter count, or winner count is zero.
    """
    profile_path = Path(file)
    seed_task(
        profile_path.parent.parent.name, profile_path.parent.name, profile_path.name, seed=seed
    )
    config = load_profile_config(profile_path)
    expected_b_proportion = compute_expected_b_proportion(config)
    n_cands = sum(len(candidates) for candidates in config.slate_to_candidates.values())
    rule_scores = {}

    for voting_rule_name in get_args(AllowedRule):
        rule = build_voting_rule(n_cands=n_cands, voting_rule_name=voting_rule_name)
        winners = rule(profile, m=3).get_elected()
        b_winners = [c for c in winners if next(iter(c)).startswith("B")]
        rule_scores[voting_rule_name] = {
            "expected_proportion": expected_b_proportion,
            "observed_proportion": len(b_winners) / len(winners),
        }

    return {file: rule_scores}


@click.command()
@click.option("--n-a-cand", type=int, required=True, help="Number of A candidates")
@click.option("--n-b-cand", type=int, required=True, help="Number of B candidates")
@click.option(
    "--b-prop",
    type=float,
    required=True,
    help="Proportion of B voters (between 0 and 1)",
)
@click.option("--a-coh", type=float, required=True, help="Cohesion of A voters (between 0 and 1)")
@click.option("--b-coh", type=float, required=True, help="Cohesion of B voters (between 0 and 1)")
@click.option(
    "--data-dir",
    "data_root",
    type=click.Path(path_type=Path),
    default=ROOT / "data",
    show_default=True,
    help="Directory containing election inputs",
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
    n_a_cand: int,
    n_b_cand: int,
    b_prop: float,
    a_coh: float,
    b_coh: float,
    *,
    data_root: Path = ROOT / "data",
    output_root: Path = ROOT,
    n_jobs: int = 1,
    seed: int = 0,
) -> None:
    """Compute and save expected and observed bloc representation for one BT parameter setting.

    Args:
        n_a_cand (int): Number of A candidates.
        n_b_cand (int): Number of B candidates.
        b_prop (float): Proportion of B voters.
        a_coh (float): Cohesion of A voters.
        b_coh (float): Cohesion of B voters.
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_jobs (int, optional): Number of parallel workers. Defaults to 1.
        seed (int, optional): Base seed for task streams. Defaults to 0.
    """
    output_root = output_root.resolve()
    data_root = data_root.resolve()
    print(f"Data: {data_root}")
    print(f"Output root: {output_root}")

    output_file = (
        output_root
        / "stats"
        / "bt_proportionality"
        / (
            f"{n_a_cand:02d}_{n_b_cand:02d}_bprop_"
            f"{b_prop:0.1f}_cohesion_({a_coh:0.2f},{b_coh:0.2f})_results.json"
        )
    )

    if output_file.exists() or output_file.is_symlink():
        print(f"Skipping existing result: {output_file}. Move it manually to recompute.")
        return

    all_profiles = load_profiles(
        n_a_cand, n_b_cand, b_prop, a_coh, b_coh, data_root=data_root, n_jobs=n_jobs
    )

    with joblib_progress(total=len(all_profiles)):
        all_file_to_rule_dicts = cast(
            list[dict[str, dict[str, dict[str, float]]]],
            Parallel(n_jobs=n_jobs, prefer="processes", batch_size="auto")(
                delayed(collect_profile_proportionality)(file, profile, seed=seed)
                for file, profile in all_profiles.items()
            ),
        )

    total_dictionary: dict[str, dict[str, dict[str, float]]] = {}

    for file_dict in all_file_to_rule_dicts:
        total_dictionary.update(file_dict)

    with new_data_file(output_file) as temporary_file, temporary_file.open("w") as f:
        json.dump(total_dictionary, f, indent=4)


if __name__ == "__main__":
    main()
