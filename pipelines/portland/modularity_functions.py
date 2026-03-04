"""
Utilities for computing modularity-like scores from matrices, including handling signed weights
and different scoring variants.

The majority of the content of these functions is copied directly from files in the github
repository

https://github.com/mcontrerassc/candidate_matrices

Doc strings have been added to clarify the purpose and behavior of each function, and some minor
adjustments have been made to ensure compatibility with the current codebase. The core logic and
structure of the functions (including most parameter names) remains unchanged.
"""

import numpy as np
from numpy.typing import NDArray
import random


def boost_modularity_matrix(A: NDArray, assignment_vec: NDArray):
    """Construct the (directed, weighted) modularity matrix for an adjacency matrix.

    See Newman (2006) "Modularity and community structure in networks" for the original
    definition of the modularity matrix for undirected, unweighted graphs. This
    implementation generalizes to directed and weighted graphs, following the same
    principle of comparing the observed adjacency to a null model based on node degrees.

    https://people.eecs.berkeley.edu/~jordan/sail/readings/newman.pdf

    Let A = P - N, where P is the positive part of A and N is the negative part of A. Then the
    modularity matrix B is defined as:

        B = A - (p_out ⊗ p_in) / p + (n_out ⊗ n_in) / n

    where:
        p_out[i] = sum_j P[i, j]
        p_in[j]  = sum_i P[i, j]
        p        = sum_{i,j} P[i, j]

        n_out[i] = sum_j N[i, j]
        n_in[j]  = sum_i N[i, j]
        n        = sum_{i,j} N[i, j]

    The diagonal of B is then set to 0, effectively ignoring self-loops in the
    modularity objective.

    Args:
        A (NDArray): Square adjacency/weight matrix of shape (n, n). Can be weighted and/or
            directed. Values are typically nonnegative for standard modularity.
        assignment_vec (NDArray): Vector of shape (n,) containing cluster assignments for
            each node. Nodes in the same cluster are considered together in the modularity
            calculation. Values should be non-negative integers representing cluster IDs.

    Returns:
        The modularity matrix B of shape (n, n), same dtype/shape as A.
    """
    A_pos = np.where(A > 0, A, 0)
    A_neg = np.where(A < 0, -A, 0)

    A_pos_sum = np.sum(A_pos)
    A_neg_sum = np.sum(A_neg)

    pos_out_vec = np.sum(A_pos, axis=1)
    pos_in_vec = np.sum(A_pos, axis=0)

    neg_out_vec = np.sum(A_neg, axis=1)
    neg_in_vec = np.sum(A_neg, axis=0)

    # Apply the delta_ij mask so we only look for things that
    # are in the same cluster
    assigment_matrix_mask = np.equal.outer(assignment_vec, assignment_vec)
    assigment_matrix_mask &= ~np.eye(
        len(assignment_vec), dtype=bool
    )  # Remove diagonal elements since we don't allow self loops
    delta_ij_positions = np.argwhere(assigment_matrix_mask)
    modularity_matrix = np.zeros_like(A, dtype=float)

    for i, j in delta_ij_positions:
        pos_wiring = pos_out_vec[i] * pos_in_vec[j] / A_pos_sum
        neg_wiring = neg_out_vec[i] * neg_in_vec[j] / A_neg_sum
        modularity_matrix[i, j] = A[i, j] - pos_wiring + neg_wiring

    return modularity_matrix


def compute_modularity(A: NDArray, assignment_vec: NDArray):
    """Compute the modularity score for a given adjacency matrix and cluster assignment.

    Note:
        Assumes that we are not allowing self-loops, so the diagonal of the modularity matrix is
        set to 0 in the boost_modularity_matrix function.

    Args:
        A (NDArray): Square adjacency/weight matrix of shape (n, n). Can be weighted and/or
            directed. Values are typically nonnegative for standard modularity.
        assignment_vec (NDArray): Vector of shape (n,) containing cluster assignments for
            each node. Nodes in the same cluster are considered together in the modularity
            calculation. Values should be non-negative integers representing cluster IDs.

    """
    modularity_matrix = boost_modularity_matrix(A, assignment_vec)
    return np.sum(modularity_matrix) / np.sum(np.abs(A))


def generate_flip_proposal(
    mutated_assignment_vec: NDArray, n_clusters: int, rng: random.Random
):
    """Generate a new cluster assignment proposal by flipping the cluster assignment of one node.

    Args:
        mutated_assignment_vec (NDArray): Current cluster assignment vector of shape (n,). This
            vector will be modified in-place to produce the new proposal.
        n_clusters (int): The total number of clusters. New cluster assignments will be in the
            range [0, n_clusters - 1].
        rng (random.Random): A random number generator instance for reproducibility.

    Returns:
        The modified cluster assignment vector with one node's cluster assignment flipped to a
        different cluster. The function ensures that flipping does not reduce the number of
        clusters by checking that the node being flipped is not the last member of its current
        cluster.
    """
    assignment_counts = np.bincount(mutated_assignment_vec, minlength=n_clusters + 1)
    found_flip = False
    to_flip = None
    while not found_flip:
        to_flip = np.random.choice(len(mutated_assignment_vec))
        # Make sure we don't reduce the number of clusters by flipping the last member of a
        # cluster to a different cluster
        if assignment_counts[mutated_assignment_vec[to_flip]] > 1:
            found_flip = True

    mutated_assignment_vec[to_flip] = rng.randint(0, n_clusters - 1)

    return mutated_assignment_vec


def run_modularity_maximization_short_bursts(
    M: NDArray,
    initial_assignment_vec: NDArray,
    n_clusters: int,
    burst_length: int,
    n_bursts: int,
    rng: random.Random,
):
    """Run modularity maximization using short bursts of local search.

    This function performs a local search to maximize the modularity score by iteratively. In
    each burst, it generates a sequence of cluster assignment proposals by flipping the cluster
    assignment of one node at a time. If a proposal has a modularity score that is greater than
    or equal to the best score found so far, it updates the best assignment and modularity score.

    Args:
        M (NDArray): Square adjacency/weight matrix of shape (n, n). Can be weighted and/or
            directed. Values are typically nonnegative for standard modularity.
        initial_assignment_vec (Sequence[int | float]): Initial cluster assignment vector of shape
            (n,). Values should be non-negative integers representing cluster IDs.
        n_clusters (int): The total number of clusters. Cluster assignments should be in the
            range [0, n_clusters - 1].
        burst_length (int): The number of local search steps to perform in each burst.
        n_bursts (int): The total number of bursts to perform.
        rng (random.Random): A random number generator instance for reproducibility.
    """
    assignment_vec = initial_assignment_vec.copy()

    best_modularity = compute_modularity(M, assignment_vec)
    best_assignment_vec = assignment_vec.copy()
    for _ in range(n_bursts):
        current_burst_assignment = best_assignment_vec.copy()
        for _ in range(burst_length):
            current_burst_assignment = generate_flip_proposal(
                current_burst_assignment, n_clusters, rng
            )
            new_modularity = compute_modularity(M, current_burst_assignment)
            if new_modularity >= best_modularity:
                best_assignment_vec = current_burst_assignment.copy()
                best_modularity = compute_modularity(M, best_assignment_vec)

    return best_assignment_vec, best_modularity
