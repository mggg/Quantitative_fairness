"""Run the short burst algorithm on the Portland profiles."""

from votekit import RankProfile
from votekit.elections import FastSTV
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.matrices import boost_matrix
from votekit.utils import mentions
import numpy as np
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).parent.resolve()
TOP_DIR = SCRIPT_DIR.parents[2]
sys.path.append(str(SCRIPT_DIR))

from modularity_functions import (  # noqa: E402
    random_partition,
    hybrid_modularity,
    fast_short_burst,
    backward_convert,
    viz_partition,
)


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


def run_short_burst_for_portland_profile_i(profile_number: int, show_viz=False):
    """Run the short burst algorithm on the given Portland profile.

    Args:
        profile_number (int): The number of the profile to run the algorithm on.
        show_viz (bool, optional): Whether to show the visualization of the partition.
            Defaults to False.
    """
    profile, boost = load_and_project(profile_number)
    cands = list(profile.candidates)

    partition2 = random_partition(len(cands), 2)
    projected_hybrid_score = hybrid_modularity(boost, "Boost")
    best_burst = fast_short_burst(partition2, projected_hybrid_score)
    print("-" * 20)
    for i, group in enumerate(backward_convert(np.array(best_burst), cands)):
        print(f"Candidate Group {i}: {group}")
    if show_viz:
        viz_partition(best_burst, boost, cands, centered=True)


if __name__ == "__main__":
    for profile_number in range(1, 5):
        print(f"Loading profile {profile_number}...", end="\r")
        run_short_burst_for_portland_profile_i(profile_number)
