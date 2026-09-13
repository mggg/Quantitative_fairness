"""Generate and save BT preference profiles and utilities."""

import argparse
import sys
from itertools import product
from pathlib import Path

import numpy as np
import votekit.ballot_generator as bg
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
from votekit import PreferenceInterval, RankProfile
from votekit.ballot_generator import BlocSlateConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import (
    BT_ALPHA_COMBINATIONS,
    BT_BLOC_PROPORTIONS,
    BT_CANDIDATE_COMBINATIONS,
    BT_COHESION_COMBINATIONS,
)
from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task


def sample_preference_interval(candidates: list[str], alpha: float) -> PreferenceInterval:
    """Draw a preference interval from the task's seeded NumPy stream.

    Args:
        candidates (list[str]): Candidate names, in the order used for the Dirichlet draw.
        alpha (float): Positive Dirichlet concentration parameter for every candidate.

    Returns:
        PreferenceInterval: Candidate support probabilities from the seeded NumPy stream.

    Raises:
        ValueError: The Dirichlet concentration parameter is nonpositive.
    """
    # VoteKit's from_dirichlet creates an unseeded generator on each call.
    return PreferenceInterval(dict(zip(candidates, np.random.dirichlet([alpha] * len(candidates)))))


def sample_profile_config(
    n_a_cands: int,
    n_b_cands: int,
    n_voters: int,
    b_proportion: float,
    a_cohesion: float,
    b_cohesion: float,
    aa_alpha: float,
    ab_alpha: float,
    ba_alpha: float,
    bb_alpha: float,
) -> BlocSlateConfig:
    """Build a two-bloc configuration by sampling its four preference intervals.

    Draw intervals in A-on-A, A-on-B, B-on-A, B-on-B order from the task's seeded stream.
    The configuration validates candidate counts, voter counts, and bloc parameters.
    """
    slate_to_candidates = {
        "bloc_1": [f"A{i + 1}" for i in range(n_a_cands)],
        "bloc_2": [f"B{i + 1}" for i in range(n_b_cands)],
    }
    return BlocSlateConfig(
        n_voters=n_voters,
        slate_to_candidates=slate_to_candidates,
        cohesion_mapping={
            "bloc_1": {"bloc_1": a_cohesion, "bloc_2": 1 - a_cohesion},
            "bloc_2": {"bloc_1": 1 - b_cohesion, "bloc_2": b_cohesion},
        },
        bloc_proportions={"bloc_1": 1 - b_proportion, "bloc_2": b_proportion},
        preference_mapping={
            "bloc_1": {
                "bloc_1": sample_preference_interval(
                    candidates=slate_to_candidates["bloc_1"],
                    alpha=aa_alpha,
                ),
                "bloc_2": sample_preference_interval(
                    candidates=slate_to_candidates["bloc_2"],
                    alpha=ab_alpha,
                ),
            },
            "bloc_2": {
                "bloc_1": sample_preference_interval(
                    candidates=slate_to_candidates["bloc_1"],
                    alpha=ba_alpha,
                ),
                "bloc_2": sample_preference_interval(
                    candidates=slate_to_candidates["bloc_2"],
                    alpha=bb_alpha,
                ),
            },
        },
    )


def generate_and_save_profile(
    n_a_cands: int,
    n_b_cands: int,
    n_voters: int,
    b_proportion: float,
    a_cohesion: float,
    b_cohesion: float,
    aa_alpha: float,
    ab_alpha: float,
    ba_alpha: float,
    bb_alpha: float,
    idx: int,
    output_base_dir: str,
    *,
    seed: int = 0,
) -> None:
    """Generate a BT profile and its preference intervals unless either output already exists.

    An existing file skips the entire pair, so new intervals are never paired with an old profile.

    Args:
        n_a_cands (int): Number of A candidates.
        n_b_cands (int): Number of B candidates.
        n_voters (int): Total number of voters to simulate.
        b_proportion (float): Proportion of B-bloc voters.
        a_cohesion (float): Cohesion of A-bloc voters.
        b_cohesion (float): Cohesion of B-bloc voters.
        aa_alpha (float): Dirichlet alpha for A-on-A preferences.
        ab_alpha (float): Dirichlet alpha for A-on-B preferences.
        ba_alpha (float): Dirichlet alpha for B-on-A preferences.
        bb_alpha (float): Dirichlet alpha for B-on-B preferences.
        idx (int): Sample index for file naming.
        output_base_dir (str): Base directory for profile outputs.
        seed (int, optional): Base seed for independent samples. Defaults to 0.

    Raises:
        FileExistsError: Another process creates a target CSV during generation.
        ValueError: The profile-generation parameters are invalid.
    """
    profile_root = Path(output_base_dir).resolve()
    utility_root = profile_root.parent / "preference_dfs"
    relative_folder = (
        f"{n_a_cands:02d}_{n_b_cands:02d}/b_proportion_{b_proportion}"
        f"__ALPHA_({aa_alpha:.2f},{ab_alpha:.2f},{ba_alpha:.2f},{bb_alpha:.2f})"
        f"__COHESION_({a_cohesion:.2f},{b_cohesion:.2f})"
    )
    output_dir = profile_root / relative_folder
    df_dir = utility_root / relative_folder
    profile_path = output_dir / f"profile_{idx}.csv"
    utility_path = df_dir / f"profile_{idx}_utilities.csv"

    for path in (profile_path, utility_path):
        if path.exists() or path.is_symlink():
            print(
                f"Skipping profile/interval pair: {path} exists."
                " Move both outputs manually to recompute."
            )
            return

    seed_task(
        n_a_cands,
        n_b_cands,
        n_voters,
        b_proportion,
        a_cohesion,
        b_cohesion,
        aa_alpha,
        ab_alpha,
        ba_alpha,
        bb_alpha,
        idx,
        seed=seed,
    )
    config = sample_profile_config(
        n_a_cands=n_a_cands,
        n_b_cands=n_b_cands,
        n_voters=n_voters,
        b_proportion=b_proportion,
        a_cohesion=a_cohesion,
        b_cohesion=b_cohesion,
        aa_alpha=aa_alpha,
        ab_alpha=ab_alpha,
        ba_alpha=ba_alpha,
        bb_alpha=bb_alpha,
    )
    profile = bg.slate_bt_profile_generator(config)
    assert isinstance(profile, RankProfile)

    with new_data_file(profile_path) as profile_file, new_data_file(utility_path) as utility_file:
        profile.to_csv(profile_file)
        config.preference_df.to_csv(utility_file)


def parse_arguments() -> argparse.Namespace:
    """Parse generation options and resolve the profile output directory.

    Returns:
        argparse.Namespace: Validated options with output_dir resolved to an absolute path.

    Raises:
        SystemExit: Voter, sample, or worker counts are nonpositive.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--n-voters", type=int, default=15_000)
    parser.add_argument("--n-samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-jobs", type=int, default=1)
    args = parser.parse_args()

    if min(args.n_voters, args.n_samples, args.n_jobs) < 1:
        parser.error("Voter, sample, and worker counts must be positive")

    args.output_dir = args.output_dir.resolve()

    return args


def main() -> None:
    """Generate the configured grid of two-bloc BT profiles in parallel.

    Raises:
        SystemExit: Command-line parsing fails or a count is nonpositive.
        FileExistsError: Another process creates a target CSV during generation.
        ValueError: The profile-generation parameters are invalid.
    """
    args = parse_arguments()
    profile_root = args.output_dir / "data/preference_profiles"
    n_voters = args.n_voters
    n_samples = args.n_samples

    b_bloc_proportions = BT_BLOC_PROPORTIONS
    alpha_combinations = BT_ALPHA_COMBINATIONS
    cohesion_combinations = BT_COHESION_COMBINATIONS
    candidate_count_combinations = BT_CANDIDATE_COMBINATIONS

    output_base_dir = str(profile_root)

    with joblib_progress(
        "Generating profiles",
        total=n_samples
        * len(b_bloc_proportions)
        * len(alpha_combinations)
        * len(cohesion_combinations)
        * len(candidate_count_combinations),
    ):
        Parallel(n_jobs=args.n_jobs)(
            delayed(generate_and_save_profile)(
                n_a_cands=n_a_cands,
                n_b_cands=n_b_cands,
                n_voters=n_voters,
                b_proportion=b_bloc_proportion,
                a_cohesion=a_coh,
                b_cohesion=b_coh,
                aa_alpha=aa_al,
                ab_alpha=ab_al,
                ba_alpha=ba_al,
                bb_alpha=bb_al,
                idx=i,
                output_base_dir=output_base_dir,
                seed=args.seed,
            )
            for (n_a_cands, n_b_cands), b_bloc_proportion, (a_coh, b_coh), (
                aa_al,
                ab_al,
                ba_al,
                bb_al,
            ), i in product(
                candidate_count_combinations,
                b_bloc_proportions,
                cohesion_combinations,
                alpha_combinations,
                list(range(n_samples)),
            )
        )


if __name__ == "__main__":
    main()
