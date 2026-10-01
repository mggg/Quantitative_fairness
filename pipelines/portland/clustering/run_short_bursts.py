"""Run the short burst algorithm on the Portland profiles."""

import argparse
import random
import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray
from tqdm.auto import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.portland.clustering.load_profile import load_projected_profile
from pipelines.portland.clustering.modularity import (  # noqa: E402
    compute_modularity,
    run_modularity_maximization_short_bursts,
)
from pipelines.portland.clustering.partition_visualization import viz_partition  # noqa: E402
from voting_metrics_main_code.replication import ROOT


class ClusteringResult(NamedTuple):
    assignment: NDArray
    score: float
    boost: NDArray
    candidates: list[str]


def run_portland_short_bursts(
    profile_number: int,
    n_clusters: int = 2,
    burst_length: int = 5,
    n_bursts: int = 200,
    rng_seed: int = 42,
    *,
    data_root: Path,
) -> ClusteringResult:
    """Run the short burst algorithm on the given Portland profile.

    Args:
        profile_number (int): The number of the profile to run the algorithm on.
        n_clusters (int, optional): The number of clusters to use. Defaults to 2.
        burst_length (int, optional): The length of each burst. Defaults to 5.
        n_bursts (int, optional): The number of bursts to run. Defaults to 200.
        rng_seed (int, optional): Seed for initialization and all search proposals. Defaults to 42.
        data_root (Path): Directory containing election inputs.

    Returns:
        ClusteringResult: Best assignment, score, boost matrix, and
            candidate names. When candidate and cluster counts match, each candidate has its
            own cluster.

    Raises:
        ValueError: The projected profile has fewer candidates than requested clusters.
    """
    if n_clusters < 1:
        raise ValueError("n_clusters must be positive")

    rng = random.Random(rng_seed)
    profile, boost = load_projected_profile(profile_number, data_root=data_root)
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

        assignment = np.arange(n_clusters)
        score = compute_modularity(boost, assignment)

        return ClusteringResult(assignment, score, boost, cands)

    assignment_vec = np.array(rng.choices(range(n_clusters), k=len(cands)))
    assignment_vec[:n_clusters] = np.arange(n_clusters)  # Keep every cluster populated.

    best_assignment_vec, best_modularity = run_modularity_maximization_short_bursts(
        boost,
        assignment_vec,
        n_clusters=n_clusters,
        burst_length=burst_length,
        n_bursts=n_bursts,
        rng=rng,
    )

    return ClusteringResult(best_assignment_vec, best_modularity, boost, cands)


def verify_clustering_stability(
    result: ClusteringResult, *, n_clusters: int, burst_length: int, n_bursts: int
) -> None:
    """Require 1,000 restart trials to retain the score and partition up to label permutation.

    This is an empirical stability diagnostic, not a proof of global optimality.

    Args:
        result (ClusteringResult): Assignment, modularity score, and boost matrix to verify.
        n_clusters (int): Number of clusters used by each restart trial.
        burst_length (int): Number of local-search steps per burst.
        n_bursts (int): Number of bursts per restart trial.

    Raises:
        RuntimeError: A trial changes the score or partition beyond a cluster-label permutation.
        ValueError: No cluster has enough candidates to allow a proposal.
    """
    expected_partition = np.equal.outer(result.assignment, result.assignment)
    for trial in tqdm(range(1000)):
        assignment, score = run_modularity_maximization_short_bursts(
            result.boost,
            result.assignment,
            n_clusters=n_clusters,
            burst_length=burst_length,
            n_bursts=n_bursts,
            rng=random.Random(trial),
        )
        if score != result.score:
            raise RuntimeError(f"Seed {trial} changed modularity from {result.score} to {score}")
        if not np.array_equal(np.equal.outer(assignment, assignment), expected_partition):
            raise RuntimeError(f"Seed {trial} found a different partition with the same modularity")


def main(show_viz: bool = False, *, data_root: Path = ROOT / "data") -> None:
    """Run Portland district 3 clustering and optionally display the resulting partition.

    Args:
        show_viz (bool, optional): Display the resulting candidate partition. Defaults to False.
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
    """
    result = run_portland_short_bursts(3, data_root=data_root)
    if len(result.candidates) > 2:
        verify_clustering_stability(result, n_clusters=2, burst_length=5, n_bursts=200)

    for cluster in range(2):
        candidates = [
            candidate
            for candidate, label in zip(result.candidates, result.assignment)
            if label == cluster
        ]
        print(f"Cluster {cluster}: {candidates}")
    print(f"Best modularity: {result.score}")

    if show_viz:
        viz_partition(result.assignment, result.boost, result.candidates, centered=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-viz", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    main(show_viz=args.show_viz, data_root=args.data_dir.resolve())
