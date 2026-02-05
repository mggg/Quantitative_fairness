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

from typing import Sequence, Callable
from tqdm.auto import tqdm
from numpy.typing import NDArray
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def make_modularity_matrix(A: NDArray[np.floating]) -> NDArray[np.floating]:
    """Construct the (directed, weighted) modularity matrix for an adjacency matrix.

    See Newman (2006) "Modularity and community structure in networks" for the original
    definition of the modularity matrix for undirected, unweighted graphs. This
    implementation generalizes to directed and weighted graphs, following the same
    principle of comparing the observed adjacency to a null model based on node degrees.

    https://people.eecs.berkeley.edu/~jordan/sail/readings/newman.pdf

    This computes the modularity matrix B defined by:

        B = A - (k_out ⊗ k_in) / m

    where:
        k_out[i] = sum_j A[i, j]
        k_in[j]  = sum_i A[i, j]
        m        = sum_{i,j} A[i, j]

    The diagonal of B is then set to 0, effectively ignoring self-loops in the
    modularity objective.

    Args:
        A: Square adjacency/weight matrix of shape (n, n). Can be weighted and/or
            directed. Values are typically nonnegative for standard modularity.

    Returns:
        The modularity matrix B of shape (n, n), same dtype/shape as A. If the
        total weight m is 0, returns an all-zeros matrix.

    Raises:
        ValueError: If A is not 2D square (optional; not enforced here).
    """
    kout = A.sum(axis=1)
    kin = A.sum(axis=0)
    m = A.sum()

    if m == 0:
        return np.zeros_like(A)

    expected = np.outer(kout, kin) / m
    B = A - expected
    # set all diagonal entries to 0
    np.fill_diagonal(B, 0)
    return B


def split_matrix(
    A: NDArray[np.floating],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Split a matrix into its positive and negative parts.

    Produces A_pos containing only positive entries (others set to 0) and A_neg
    containing only negative entries (others set to 0).

    Args:
        A: Input matrix of any shape.

    Returns:
        A tuple (A_pos, A_neg) with the same shape as A:
            - A_pos[i, j] = A[i, j] if A[i, j] > 0 else 0
            - A_neg[i, j] = A[i, j] if A[i, j] < 0 else 0
    """
    A_pos = np.where(A > 0, A, 0)
    A_neg = np.where(A < 0, A, 0)
    return A_pos, A_neg


def modularity_from_B(
    B: NDArray[np.floating],
    m: float,
    assignment: Sequence[int],
    mod_type: str = "standard",
    pm: str = "pos",
) -> float:
    """Compute a modularity-like score from a precomputed modularity matrix.

    This function sums entries of B over all ordered pairs (i, j), applying a rule
    that depends on `mod_type` and `pm`, and then normalizes by `m`.

    Interpretation (high-level):
        - `pm="pos"` treats within-group pairs as "aligned" (reward/punish depending
          on mod_type).
        - `pm="neg"` treats between-group pairs as "aligned" (reward/punish depending
          on mod_type).

    The behaviors:
        - mod_type="standard":
            Add B[i, j] only for "aligned" pairs.
        - mod_type="hybrid":
            Add B[i, j] for aligned pairs, subtract B[i, j] for non-aligned pairs.
        - mod_type="reverse":
            Subtract B[i, j] only for aligned pairs (with reversed alignment rule).

    Args:
        B: Modularity matrix of shape (n, n).
        m: Normalization constant. Typically the total weight used to build B.
            If m == 0, the function returns 0.0.
        assignment: Community labels of length n. Nodes i and j are in the same
            group if assignment[i] == assignment[j].
        mod_type: Scoring variant. One of {"standard", "hybrid", "reverse"}.
        pm: Pairing mode. One of {"pos", "neg"}.

    Returns:
        The computed modularity-like score (float), normalized by m.

    Raises:
        AssertionError: If pm is not in {"pos", "neg"}.
        ValueError: If mod_type is unrecognized.
    """
    assert pm in {"pos", "neg"}
    n = len(assignment)
    Q = 0.0
    if m == 0:
        return 0.0

    for i in range(n):
        for j in range(n):
            same_group = assignment[i] == assignment[j]
            if mod_type == "standard":
                if (pm == "pos" and same_group) or (pm == "neg" and not same_group):
                    Q += B[i, j]
            elif mod_type == "hybrid":
                if (pm == "pos" and same_group) or (pm == "neg" and not same_group):
                    Q += B[i, j]
                else:
                    Q -= B[i, j]
            elif mod_type == "reverse":
                if (pm == "pos" and not same_group) or (pm == "neg" and same_group):
                    Q -= B[i, j]
            else:
                raise ValueError(f"Unknown mod_type: {mod_type}")

    return Q / m


def hybrid_modularity(
    M: NDArray[np.floating],
    matrix_name: str,
) -> Callable[[Sequence[int]], float]:
    """Build a signed 'hybrid' modularity scoring function for a matrix.

    This constructs separate modularity matrices for positive and negative parts
    of `M`:

        - For positive entries: use A = max(M, 0) and compute A_mod = modularity(A).
        - For negative entries: use B = min(M, 0), take magnitudes -B, and compute
          B_mod = modularity(-B).

    The returned scoring function combines:
        Q_A: standard modularity reward for keeping positive structure within groups.
        Q_B: "negative" modularity term rewarding negative structure across groups.

    The final score is returned as:
        score = -Q_A - Q_B

    Args:
        M: Square matrix of shape (n, n) that may contain positive and negative
            entries (e.g., signed weights).
        matrix_name: Name used to label the returned scoring function.

    Returns:
        A function `score(partition)` that maps an assignment (sequence of length n)
        to a float score. The function has an attribute `score_name` set to
        f"{matrix_name}_hybrid".
    """
    A, B = split_matrix(M)
    A_mod = make_modularity_matrix(A)
    m_A = A.sum()
    B_mod = make_modularity_matrix(-B)
    m_B = -B.sum()

    def score(partition8: Sequence[int]) -> float:
        """Score a partition using the precomputed signed modularity matrices.

        Args:
            partition8: Community labels of length n.

        Returns:
            Signed hybrid modularity score (negative of the combined modularities).
        """
        Q_A = modularity_from_B(A_mod, m_A, partition8, mod_type="standard", pm="pos")
        Q_B = modularity_from_B(B_mod, m_B, partition8, mod_type="standard", pm="neg")
        return -Q_A - Q_B

    score.__setattr__("score_name", f"{matrix_name}_hybrid")
    return score


def random_partition(n_cands: int, n_parts: int):
    """Generate a random partition of n_cands candidates into n_parts parts.

    Args:
        n_cands (int): Total number of candidates (length of the partition).
        n_parts (int): Number of parts/groups to partition into.
    """
    accept = False
    while not accept:
        cand = np.random.randint(0, n_parts, size=n_cands)
        if len(set(cand)) == n_parts:
            accept = True
    return cand


def fast_proposal_generator(
    partition8: Sequence[int],
) -> Callable[[Sequence[int]], Sequence[int]]:
    """Generate a proposal function that makes a small random change to a partition.

    Args:
        partition8: A sequence of community labels (length n) representing a partition.
    """
    k = max(partition8)
    ncand = len(partition8)

    def fast_proposal(partition):
        new_partition = partition.copy()
        new_partition[np.random.randint(0, ncand)] = np.random.randint(0, k + 1)
        return new_partition

    return fast_proposal


def fast_short_burst(
    starting_partition: Sequence[int],
    score_fn: Callable[[Sequence[int]], float],
    proposal_gen: Callable[
        [Sequence[int]], Callable[[Sequence[int]], Sequence[int]]
    ] = fast_proposal_generator,
    burst_size=40,
    num_bursts=50,
) -> Sequence[int]:
    """Perform a short burst of local search to improve a partition.


    Args:
        starting_partition (Sequence[int]): Initial partition to start from (sequence of ints
            representing candidate clustering).
        score_fn (Callable[[Sequence[int]], float]): A function that takes a partition and returns
            a score.
        proposal_gen (Callable[[Sequence[int]], Callable[[Sequence[int]], Sequence[int]]], optional):
            A function that generates a proposal function for making local changes to the partition.
            Defaults to `fast_proposal_generator`.
        burst_size (int, optional): Number of local steps to take in each burst. Defaults to 40.
        num_bursts (int, optional): Number of bursts to perform. Defaults to 50.
    Returns:
        The best partition found after performing the bursts.
    """
    status_quo = score_fn(starting_partition)
    if not hasattr(score_fn, "score_name"):
        score_fn.__setattr__("score_name", "unnamed_score_fn")

    burst_best = starting_partition.copy()  # ty: ignore
    proposal = proposal_gen(burst_best)
    for _ in tqdm(range(num_bursts)):
        trial_step = burst_best
        for _ in range(burst_size):
            trial_step = proposal(trial_step)
            quo = score_fn(trial_step)
            if quo <= status_quo:
                burst_best = trial_step.copy()  # ty: ignore
                status_quo = float(quo)
    return burst_best


def show_matrix(
    M: NDArray,
    title: str | None = None,
    labels: list[str] | None = None,
    cmap: str = "viridis",
    boundaries: Sequence[int] | None = None,
    centered: bool = False,
    log_scale: bool = False,
):
    """A simple function to display the boost matrix

    Args:
        M (NDArray): The matrix to display.
        title (str, optional): The title of the plot. Defaults to None.
        labels (list[str], optional): Labels for the axes. Defaults to None.
        cmap (str, optional): Colormap to use. Defaults to 'viridis'.
        boundaries (list[int], optional): Boundaries to draw on the matrix. Defaults to None.
        centered (bool, optional): Whether to center the colormap around zero. Defaults to False.
        log_scale (bool, optional): Whether to use a symmetric log scale for the colormap.
            Defaults to False.
    """
    fig, ax = plt.subplots()

    if centered:
        data = np.asarray(M)
        max_abs = np.max(np.abs(data))
        if max_abs == 0:
            norm = None
        elif log_scale:
            # Symmetric log scaling around zero to make tiny deviations visible
            linthresh = max(max_abs * 0.01, 1e-12)
            norm = mcolors.SymLogNorm(
                linthresh=linthresh, linscale=1.0, vmin=-max_abs, vmax=max_abs, base=10
            )
        else:
            norm = mcolors.Normalize(vmin=-max_abs, vmax=max_abs)
    else:
        vmin = np.min(M)
        vmax = np.max(M)
        norm = None if vmin == vmax else mcolors.Normalize(vmin=vmin, vmax=vmax)

    if title:
        plt.title(title)

    img = ax.imshow(M, cmap=cmap, norm=norm)
    fig.colorbar(img)

    if labels:
        ax.set_xticks(range(M.shape[1]), minor=False)
        ax.set_yticks(range(M.shape[0]), minor=False)
        ax.grid(False)
        ax.set_xticklabels(labels)
        ax.set_yticklabels(labels)
        ax.tick_params(axis="x", labelrotation=90)
        ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)

    ax.set_aspect("auto")

    if boundaries is not None and len(boundaries) > 0:
        for b in boundaries:
            ax.axhline(b - 0.5, color="black", linewidth=1)
            ax.axvline(b - 0.5, color="black", linewidth=1)

    plt.show()


def backward_convert(
    array: NDArray, canonical_candidates: list[str]
) -> list[list[str]]:
    """Convert a numpy array back into a partition (list of lists).

    Args:
        array (NDArray): A 1D array of community labels for each candidate, where the value at
            index j indicates the community assignment of candidate j.)
        canonical_candidates (list[str]): A list of candidate names corresponding to the indices
            in `array`.
    """
    cand_dict = {i: candidate for i, candidate in enumerate(canonical_candidates)}
    partition = []
    for i in range(max(array) + 1):
        bloc = [cand_dict[j] for j in range(len(array)) if array[j] == i]
        partition.append(bloc)
    return partition


def viz_partition(
    partition: list[list[str]] | NDArray[np.integer],
    boost: NDArray,
    candidates: list[str],
    cmap: str = "PRGn",
    centered: bool = False,
):
    """Visualize the boost matrix reordered according to a given partition.


    Args:
        partition (list[list[str]]): A partition of candidates into blocks, where each block is a
            list of candidate names.
        boost (NDArray): The boost matrix to visualize.
        candidates (list[str]): The list of candidate names corresponding to the order of the boost
            matrix.
        cmap (str, optional): Colormap to use for visualization. Defaults to 'PRGn'.
        centered (bool, optional): Whether to center the colormap around zero. Defaults to False.
    """
    if isinstance(partition, np.ndarray):
        partish = backward_convert(partition, candidates)
    else:
        partish = partition.copy()
    ordering = [c for bloc in partish for c in bloc]
    permutation_list = []
    for candidate in candidates:
        permutation_list.append(ordering.index(candidate))
    permutation_matrix = np.zeros((len(candidates), len(candidates)))
    for i, p in enumerate(permutation_list):
        permutation_matrix[i, p] = 1

    # determine boundaries between blocks
    block_sizes = [len(b) for b in partish]
    boundaries = np.cumsum(block_sizes)[:-1]  # omit final edge

    show_matrix(
        permutation_matrix.T @ boost @ permutation_matrix,
        labels=ordering,
        cmap=cmap,
        boundaries=list(boundaries),
        centered=centered,
    )
