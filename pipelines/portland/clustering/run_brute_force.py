"""Find exhaustive modularity optima for Portland candidate clusters.

Compare these optima with the assignments found by heuristic optimization.
"""

import argparse
import sys
from math import comb
from pathlib import Path
from typing import Self, cast

import numpy as np
from numpy.typing import NDArray
from votekit import RankProfile
from votekit.cleaning import remove_and_condense_rank_profile
from votekit.elections import FastSTV
from votekit.matrices import boost_matrix
from votekit.utils import mentions

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.portland.clustering.modularity import compute_modularity  # noqa: E402
from voting_metrics_main_code.replication import ROOT


def load_and_project(profile_number: int, *, data_root: Path) -> tuple[RankProfile, NDArray]:
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

    elec = FastSTV(profile, m=3)
    mentions_dict = mentions(profile)

    non_viable_cands = [cand for cand in candidates if mentions_dict[cand] < elec.threshold]

    projected_profile = remove_and_condense_rank_profile(non_viable_cands, profile)
    projected_boost = boost_matrix(projected_profile, candidates=list(projected_profile.candidates))

    projected_boost = np.nan_to_num(projected_boost)

    return projected_profile, projected_boost


class PartitionAssignments:
    """Iterate over candidate assignments with optional trivial-vector and required-parts filters.

    Assignments have n_cands entries with labels from 0 through k_parts - 1.
    """

    def __init__(
        self,
        n_cands: int,
        k_parts: int,
        *,
        exclude_trivial: bool = True,
        require_all_parts_used: bool = True,
    ) -> None:
        """Initialize the generator.

        Args:
            n_cands (int): The number of candidates (length of vectors).
            k_parts (int): The number of parts (labels 0..k-1).
            exclude_trivial (bool, optional): If True, skip vectors where all entries are the same.
                Defaults to True.
            require_all_parts_used (bool, optional): If True, only yield vectors that use all k
                parts at least once. Defaults to True.

        Raises:
            ValueError: n_cands is below one or k_parts is below two.
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

    def __iter__(self) -> Self:
        """Return this stateful iterator without resetting its current position.

        Returns:
            Self: This iterator at its current position.
        """
        return self

    def _to_base_k_vec(self, x: int) -> list[int]:
        """Convert an integer x to a length-n_cands vector of digits in base k_parts.

        For example, if n_cands=3 and k_parts=2, then x=5 would convert to [1,0,1] since 5 in
        base 2 is 101.

        Args:
            x (int): The integer to convert, in the range [0, k_parts**n_cands).

        Returns:
            list[int]: Base-k digits in most-significant-first order, padded to n_cands entries.
        """
        vec = [0] * self.n_cands
        k = self.k_parts

        for i in range(self.n_cands - 1, -1, -1):
            x, r = divmod(x, k)
            vec[i] = r

        return vec

    def _accept(self, vec: list[int]) -> bool:
        """Check an assignment against the trivial-vector and required-parts filters.

        Args:
            vec (list[int]): The vector to check, should be of length n_cands with entries in
                0..k_parts-1.

        Returns:
            bool: Whether the assignment satisfies both configured filtering rules.
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

    def __next__(self) -> list[int]:
        """Advance to the next assignment satisfying the configured filtering rules.

        Returns:
            list[int]: Next accepted candidate-label vector in base-k counting order.

        Raises:
            StopIteration: All k_parts**n_cands assignments have been considered.
        """
        while self.current < self.max_val:
            vec = self._to_base_k_vec(self.current)
            self.current += 1

            if self._accept(vec):
                return vec

        raise StopIteration

    def __len__(self) -> int:
        """Count all accepted assignments, including any already consumed.

        Returns:
            int: Total assignments satisfying the configured filtering rules.
        """
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


def main(*, data_root: Path = ROOT / "data") -> None:
    """Print exhaustive best modularity assignments for Portland districts and two to four parts.

    Args:
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
    """
    data_root = data_root.resolve()
    print(f"Data: {data_root}")

    for n_parts in range(2, 5):
        print("=" * 50)
        print(f"  {n_parts} PARTS  ".center(50, "="))
        print("=" * 50)

        for i in range(1, 5):
            print(f"Loading profile {i}...", end="\r")
            profile, boost = load_and_project(i, data_root=data_root)
            cands = list(profile.candidates)

            max_score = float("-inf")
            best_vec = None

            for vec in PartitionAssignments(len(cands), n_parts):
                modularity = compute_modularity(boost, np.asarray(vec))

                if modularity > max_score:
                    max_score = modularity
                    best_vec = vec

            print("Best vec:", best_vec)
            print("Max score:", max_score)

            for j in range(n_parts):
                print(
                    f"Candidate Group {j}:",
                    np.array(cands)[np.array(best_vec) == j].tolist(),
                )

            print("-------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    main(data_root=args.data_dir)
