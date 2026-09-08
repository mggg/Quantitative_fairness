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
from voting_metrics_main_code.replication import RESULTS_DIR, check_output_directory, seed_task


def sample_preference_interval(candidates: list[str], alpha: float) -> PreferenceInterval:
    """Draw a preference interval from the task's seeded NumPy stream."""
    # VoteKit's from_dirichlet creates an unseeded generator on each call.
    return PreferenceInterval(dict(zip(candidates, np.random.dirichlet([alpha] * len(candidates)))))


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
) -> None:
    """Generate a single BT profile and save to disk.

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
    profile_path = check_output_directory(output_dir / f"profile_{idx}.csv")
    utility_path = check_output_directory(df_dir / f"profile_{idx}_utilities.csv")
    for path in (profile_path, utility_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Preserving existing generated data: {path}")
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
    )
    slate_to_candidates = {
        "bloc_1": [f"A{i + 1}" for i in range(n_a_cands)],
        "bloc_2": [f"B{i + 1}" for i in range(n_b_cands)],
    }
    config = BlocSlateConfig(
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
    prof = bg.slate_bt_profile_generator(config)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(df_dir).mkdir(parents=True, exist_ok=True)
    assert isinstance(prof, RankProfile)
    prof.to_csv(profile_path)
    config.preference_df.to_csv(utility_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR / "data/preference_profiles")
    parser.add_argument("--n-voters", type=int, default=15_000)
    parser.add_argument("--n-samples", type=int, default=100)
    parser.add_argument("--n-jobs", type=int, default=1)
    args = parser.parse_args()
    if min(args.n_voters, args.n_samples, args.n_jobs) < 1:
        parser.error("Voter, sample, and worker counts must be positive")
    profile_root = check_output_directory(args.output_dir)
    utility_root = check_output_directory(profile_root.parent / "preference_dfs")
    if profile_root.exists() or utility_root.exists():
        parser.error("Profile or utility directory already exists; choose a new --output-dir")
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
