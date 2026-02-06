"""
Run brute-force optimization of the modularity-like score for clustering candidates, to check
how well the heuristic optimization does.
"""

from votekit import RankProfile
from votekit.elections import FastSTV
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.matrices import boost_matrix
from votekit.utils import mentions
import numpy as np
from pathlib import Path
import sys
from math import comb

SCRIPT_DIR = Path(__file__).parent.resolve()
TOP_DIR = SCRIPT_DIR.parents[1]
sys.path.append(str(SCRIPT_DIR))

from modularity_functions import hybrid_modularity  # noqa: E402


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


class YieldAllKPartitionVecs:
    """Generate all length-n_cands vectors of labels 0..k_parts-1, with options to exclude trivial
    vectors and require all parts used.
    """

    def __init__(
        self,
        n_cands: int,
        k_parts: int,
        *,
        exclude_trivial: bool = True,
        require_all_parts_used: bool = True,
    ):
        """Initialize the generator.

        Args:
            n_cands (int): The number of candidates (length of vectors).
            k_parts (int): The number of parts (labels 0..k-1).
            exclude_trivial (bool): If True, skip vectors where all entries are the same.
            require_all_parts_used (bool): If True, only yield vectors that use all k parts at
                least once.
        """
        if n_cands <= 0:
            raise ValueError("n_cands must be >= 1")
        if k_parts <= 1:
            raise ValueError("k_parts must be >= 2")

        self.n_cands = n_cands
        self.k_parts = k_parts
        self.exclude_trivial = exclude_trivial
        self.require_all_parts_used = require_all_parts_used

        self.max_val = k_parts**n_cands  # count of all vectors
        self.current = 0

    def __iter__(self):
        return self

    def _to_base_k_vec(self, x: int):
        """Convert an integer x to a length-n_cands vector of digits in base k_parts.

        For example, if n_cands=3 and k_parts=2, then x=5 would convert to [1,0,1] since 5 in
        base 2 is 101.

        Args:
            x (int): The integer to convert, should be in the range [0, k
        """
        vec = [0] * self.n_cands
        k = self.k_parts
        for i in range(self.n_cands - 1, -1, -1):
            x, r = divmod(x, k)
            vec[i] = r
        return vec

    def _accept(self, vec: list[int]):
        """Check if the vector vec should be accepted based on the exclude_trivial and
        require_all_parts_used options.

        Args:
            vec (List[int]): The vector to check, should be of length n_cands with entries in
            0..k_parts-1.
        """
        if self.exclude_trivial:
            # skip constant vectors like [0,0,0] or [2,2,2]
            if all(v == vec[0] for v in vec):
                return False
        if self.require_all_parts_used:
            # ensure every label 0..k-1 appears at least once
            if len(set(vec)) < self.k_parts:
                return False
        return True

    def __next__(self):
        while self.current < self.max_val:
            vec = self._to_base_k_vec(self.current)
            self.current += 1
            if self._accept(vec):
                return vec
        raise StopIteration

    def __len__(self):
        k, n = self.k_parts, self.n_cands

        if self.require_all_parts_used:
            # number of surjections onto k labeled parts:
            # sum_{i=0..k} (-1)^i * C(k,i) * (k-i)^n
            total = 0
            for i in range(0, k + 1):
                total += ((-1) ** i) * comb(k, i) * ((k - i) ** n)
            return total
        else:
            total = k**n
            if self.exclude_trivial:
                total -= k
            return total


if __name__ == "__main__":
    for n_parts in range(2, 5):
        print("=" * 50)
        print(f"  {n_parts} PARTS  ".center(50, "="))
        print("=" * 50)
        for i in range(1, 5):
            print(f"Loading profile {i}...", end="\r")
            profile, boost = load_and_project(i)
            cands = list(profile.candidates)

            mod_score_function = hybrid_modularity(boost, "Boost")
            max_score = float("-inf")
            best_vec = None
            for vec in YieldAllKPartitionVecs(len(cands), n_parts):
                if abs(mod_score_function(vec)) > max_score:
                    max_score = abs(mod_score_function(vec))
                    best_vec = vec
            print("Best vec:", best_vec)
            print("Max score:", max_score)
            for j in range(n_parts):
                print(
                    f"Candidate Group {j}:",
                    np.array(cands)[np.array(best_vec) == j].tolist(),
                )
            print("-------------------")
