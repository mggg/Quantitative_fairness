"""Run the short burst algorithm on the Portland profiles."""

import argparse
import random
import sys
from pathlib import Path

import numpy as np
from votekit import RankProfile
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.elections import FastSTV
from votekit.matrices import boost_matrix
from votekit.utils import mentions

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.portland.clustering.modularity import (  # noqa: E402
    compute_modularity,
    run_modularity_maximization_short_bursts,
)
from pipelines.portland.clustering.partition_visualization import viz_partition  # noqa: E402

from voting_metrics_main_code.replication import DATA_DIR


def load_and_project(profile_number: int):
    """Load in the profile and project it to the viable candidates.

    Candidates with mentions below the three-seat STV threshold are removed.
    Nonfinite boost entries are replaced using NumPy’s nan_to_num defaults.

    Args:
        profile_number (int): The number of the profile to load and project.

    Returns:
        tuple[RankProfile, np.ndarray]: Projected profile and boost matrix in its candidate order.

    Raises:
        FileNotFoundError: The requested Portland profile CSV does not exist.
    """
    profile = RankProfile.from_csv(f"{DATA_DIR}/Portland_D{profile_number}_cleaned_votekit.csv")
    candidates = list(profile.candidates)

    elec = FastSTV(profile, m=3)  # ty: ignore
    mentions_dict = mentions(profile)  # ty: ignore

    non_viable_cands = [cand for cand in candidates if mentions_dict[cand] < elec.threshold]

    projected_profile = remove_and_condense_rank_profile(non_viable_cands, profile)  # ty: ignore
    projected_boost = boost_matrix(projected_profile, candidates=list(projected_profile.candidates))
    projected_boost = np.nan_to_num(projected_boost)

    return projected_profile, projected_boost


def run_short_burst_for_portland_profile_i(
    profile_number: int,
    n_clusters: int = 2,
    burst_length: int = 5,
    n_bursts: int = 200,
    rng_seed: int = 42,
):
    """Run the short burst algorithm on the given Portland profile.

    Args:
        profile_number (int): The number of the profile to run the algorithm on.
        n_clusters (int, optional): The number of clusters to use. Defaults to 2.
        burst_length (int, optional): The length of each burst. Defaults to 5.
        n_bursts (int, optional): The number of bursts to run. Defaults to 200.
        rng_seed (int, optional): Seed for the label-choice RNG; NumPy candidate draws are not
            seeded here. Defaults to 42.

    Returns:
        tuple[np.ndarray, float, np.ndarray, list[str]] | tuple[list[int], float]: Normally the best
            assignment, score, boost matrix, and candidate names. When the candidate count equals
            the cluster count, only the trivial assignment and score are returned.

    Raises:
        ValueError: The projected profile has fewer candidates than requested clusters.
        Exception: A verification trial changes the modularity score or finds an assignment
                different from the best assignment and its binary-label complement.
    """
    rng = random.Random(rng_seed)
    profile, boost_matrix = load_and_project(profile_number)
    cands = list(profile.candidates)

    if len(cands) < n_clusters:
        raise ValueError(
            f"Profile {profile_number} has fewer candidates than the number of clusters."
        )

    if len(cands) == n_clusters:
        print(
            f"Profile {profile_number} has the same number of candidates as clusters."
            f" Returning trivial assignment."
        )

        return list(range(n_clusters)), compute_modularity(boost_matrix, np.arange(n_clusters))

    assignment_vec = np.random.randint(0, n_clusters - 1, size=len(cands))

    # Just make sure that each cluster has at least one member to start with
    for i in range(n_clusters):
        assignment_vec[i] = i

    best_assignment_vec, best_modularity = run_modularity_maximization_short_bursts(
        boost_matrix,
        assignment_vec,
        n_clusters=n_clusters,
        burst_length=burst_length,
        n_bursts=n_bursts,
        rng=rng,
    )

    from tqdm.auto import tqdm

    for trial in tqdm(range(1000)):
        fresh_rng = random.Random(trial)
        new_assignment_vec, new_modularity = run_modularity_maximization_short_bursts(
            boost_matrix,
            best_assignment_vec,
            n_clusters=n_clusters,
            burst_length=burst_length,
            n_bursts=n_bursts,
            rng=fresh_rng,
        )

        if new_modularity != best_modularity:
            print(f"SEED {trial}:")
            print(f"Improved modularity from {best_modularity} to {new_modularity}")
            raise Exception("Modularity improved after 1000 bursts, which shouldn't happen.")

        if np.any(new_assignment_vec != best_assignment_vec) and np.any(
            new_assignment_vec != 1 - best_assignment_vec
        ):
            print(f"SEED {trial}:")
            print("Found a different assignment with the same modularity, which shouldn't happen.")
            print(f"new {new_assignment_vec}")
            print(f"old {best_assignment_vec}")
            raise Exception(
                "Found a different assignment with the same modularity, which shouldn't happen."
            )

    candidates = list(profile.candidates)

    for i in range(n_clusters):
        cluster_cands = [
            candidates[j] for j in range(len(candidates)) if best_assignment_vec[j] == i
        ]
        print(f"Cluster {i}: {cluster_cands}")

    print(f"Best modularity: {best_modularity}")

    return best_assignment_vec, best_modularity, boost_matrix, cands


def main() -> None:
    """Run Portland district 3 clustering and optionally display the resulting partition."""
    parser = argparse.ArgumentParser(description="Run short burst on Portland profiles.")
    parser.add_argument(
        "--show-viz",
        action="store_true",
        help="Whether to show the visualization of the partition.",
    )
    args = parser.parse_args()

    # for profile_number in range(1, 5):
    for profile_number in [3]:
        tag_string = f"== PROFILE {profile_number} =="
        print("=" * len(tag_string))
        print(tag_string)
        print("=" * len(tag_string))
        print(f"Loading profile {profile_number}...", end="\r")
        best_vec, _, boost_mat, cand_list = run_short_burst_for_portland_profile_i(profile_number)

        print()

        if args.show_viz:
            viz_partition(best_vec, boost_mat, cand_list, centered=True)


if __name__ == "__main__":
    main()
