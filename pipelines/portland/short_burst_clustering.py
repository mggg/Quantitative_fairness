"""Run the short burst algorithm on the Portland profiles."""

from votekit import RankProfile
from votekit.elections import FastSTV
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.matrices import boost_matrix
from votekit.utils import mentions
import random
import argparse
import numpy as np
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).parent.resolve()
TOP_DIR = SCRIPT_DIR.parents[1]
sys.path.append(str(SCRIPT_DIR))

from modularity_functions import (  # noqa: E402
    run_modularity_maximization_short_bursts,
    compute_modularity,
)

from modularity_viz import viz_partition  # noqa: E402


def load_and_project(profile_number: int):
    """Load in the profile and project it to the viable candidates.

    Args:
        profile_number (int): The number of the profile to load and project.
    """

    profile = RankProfile.from_csv(
        f"{TOP_DIR}/data/Portland_D{profile_number}_cleaned_votekit.csv"
    )
    candidates = list(profile.candidates)

    elec = FastSTV(profile, m=3)  # ty: ignore
    mentions_dict = mentions(profile)  # ty: ignore

    non_viable_cands = [
        cand for cand in candidates if mentions_dict[cand] < elec.threshold
    ]

    projected_profile = remove_and_condense_rank_profile(non_viable_cands, profile)  # ty: ignore
    projected_boost = boost_matrix(
        projected_profile, candidates=list(projected_profile.candidates)
    )
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
        rng_seed (int, optional): The random seed for reproducibility. Defaults to 42.

    Returns:
        best_assignment_vec (NDArray): The best cluster assignment vector found by the algorithm.
        best_modularity (float): The modularity score of the best assignment.
        boost_matrix (NDArray): The boost matrix used for the modularity calculations.
        cands (list[str]): The list of candidate names corresponding to the order of the boost
            matrix.
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
            f"Profile {profile_number} has the same number of candidates as clusters. Returning trivial assignment."
        )
        return list(range(n_clusters)), compute_modularity(
            boost_matrix, np.arange(n_clusters)
        )

    assignemnt_vec = np.random.randint(0, n_clusters - 1, size=len(cands))

    # Just make sure that each cluster has at least one member to start with
    for i in range(n_clusters):
        assignemnt_vec[i] = i

    best_assignment_vec, best_modularity = run_modularity_maximization_short_bursts(
        boost_matrix,
        assignemnt_vec,
        n_clusters=n_clusters,
        burst_length=burst_length,
        n_bursts=n_bursts,
        rng=rng,
    )

    candidates = list(profile.candidates)
    for i in range(n_clusters):
        cluster_cands = [
            candidates[j] for j in range(len(candidates)) if best_assignment_vec[j] == i
        ]
        print(f"Cluster {i}: {cluster_cands}")
    print(f"Best modularity: {best_modularity}")

    return best_assignment_vec, best_modularity, boost_matrix, cands


if __name__ == "__main__":
    arger = argparse.ArgumentParser(description="Run short burst on Portland profiles.")
    arger.add_argument(
        "--show-viz",
        action="store_true",
        help="Whether to show the visualization of the partition.",
    )
    args = arger.parse_args()

    for profile_number in range(1, 5):
        tag_string = f"== PROFILE {profile_number} =="
        print("=" * len(tag_string))
        print(tag_string)
        print("=" * len(tag_string))
        print(f"Loading profile {profile_number}...", end="\r")
        best_vec, _, boost_mat, cand_list = run_short_burst_for_portland_profile_i(
            profile_number
        )
        print()
        if args.show_viz:
            viz_partition(best_vec, boost_mat, cand_list, centered=True)
