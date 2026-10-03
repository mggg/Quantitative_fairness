"""Find exhaustive modularity optima for Portland candidate clusters.

Compare these optima with the assignments found by heuristic optimization.
"""

import argparse
import sys
from collections.abc import Iterator
from itertools import product
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.portland.clustering.load_profile import load_projected_profile
from pipelines.portland.clustering.modularity import compute_modularity  # noqa: E402
from voting_metrics_main_code.replication import ROOT


def iter_partition_assignments(n_cands: int, n_parts: int) -> Iterator[tuple[int, ...]]:
    """Yield candidate assignments using every cluster label, in lexicographic order.

    Raises:
        ValueError: Candidate count is below one or the number of parts is below two.
    """
    if n_cands < 1:
        raise ValueError("n_cands must be >= 1")
    if n_parts < 2:
        raise ValueError("n_parts must be >= 2")

    return (
        assignment
        for assignment in product(range(n_parts), repeat=n_cands)
        if len(set(assignment)) == n_parts
    )


def main(*, data_root: Path = ROOT / "data") -> None:
    """Print exhaustive best modularity assignments for Portland districts and two to four parts.

    Args:
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
    """
    data_root = data_root.resolve()

    for n_parts in range(2, 5):
        print("=" * 50)
        print(f"  {n_parts} PARTS  ".center(50, "="))
        print("=" * 50)

        for i in range(1, 5):
            print(f"Loading profile {i}...", end="\r")
            profile, boost = load_projected_profile(i, data_root=data_root)
            cands = list(profile.candidates)

            max_score = float("-inf")
            best_vec = None

            for vec in iter_partition_assignments(len(cands), n_parts):
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
