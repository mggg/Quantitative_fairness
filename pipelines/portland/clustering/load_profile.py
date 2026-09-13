"""Load Portland profiles and project boost matrices onto viable candidates."""

from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray
from votekit import RankProfile
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.elections import FastSTV
from votekit.matrices import boost_matrix
from votekit.utils import mentions


def load_projected_profile(profile_number: int, *, data_root: Path) -> tuple[RankProfile, NDArray]:
    """Load in the profile and project it to the viable candidates.

    Candidates with mentions below the three-seat STV threshold are removed.
    Nonfinite boost entries are replaced using NumPy’s nan_to_num defaults.

    Args:
        data_root (Path): Directory containing election inputs.
        profile_number (int): The number of the profile to load and project.

    Returns:
        tuple[RankProfile, NDArray]: Projected profile and boost matrix in its candidate order.

    Raises:
        FileNotFoundError: The requested Portland profile CSV does not exist.
    """
    profile = cast(
        RankProfile,
        RankProfile.from_csv(f"{data_root}/Portland_D{profile_number}_cleaned_votekit.csv"),
    )
    candidates = list(profile.candidates)

    election = FastSTV(profile, m=3)
    mentions_dict = mentions(profile)

    non_viable_cands = [cand for cand in candidates if mentions_dict[cand] < election.threshold]

    projected_profile = remove_and_condense_rank_profile(non_viable_cands, profile)
    projected_boost = boost_matrix(projected_profile, candidates=list(projected_profile.candidates))

    projected_boost = np.nan_to_num(projected_boost)

    return projected_profile, projected_boost
