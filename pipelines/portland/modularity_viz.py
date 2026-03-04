"""
Utilities for vizualizing the boost matrix and partitions of candidates.

The majority of the content of these functions is copied directly from files in the github
repository

https://github.com/mcontrerassc/candidate_matrices

Doc strings have been added to clarify the purpose and behavior of each function, and some minor
adjustments have been made to ensure compatibility with the current codebase. The core logic and
structure of the functions (including most parameter names) remains unchanged.
"""

from typing import Sequence, TypeGuard
import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


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


def _is_partition_blocks(
    partition: Sequence[object],
) -> TypeGuard[Sequence[Sequence[str]]]:
    """Check if the partition is given as a 1D array of labels."""
    if len(partition) == 0:
        return False
    return isinstance(partition[0], (list, tuple, set, frozenset))


def viz_partition(
    partition: list[list[str]] | NDArray[np.integer] | Sequence[int],
    boost: NDArray,
    candidates: list[str],
    cmap: str = "PRGn",
    centered: bool = False,
):
    """Visualize the boost matrix reordered according to a given partition.


    Args:
        partition (list[list[str]] | NDArray[np.integer] | Sequence[int]): A partition of
            candidates into blocks. Can be provided as:
            - A list of lists of candidate names (explicit blocks).
            - A 1D integer array of community labels (one per candidate).
            - A sequence of integer labels (one per candidate).
        boost (NDArray): The boost matrix to visualize.
        candidates (list[str]): The list of candidate names corresponding to the order of the boost
            matrix.
        cmap (str, optional): Colormap to use for visualization. Defaults to 'PRGn'.
        centered (bool, optional): Whether to center the colormap around zero. Defaults to False.
    """
    if isinstance(partition, np.ndarray):
        partish = backward_convert(partition, candidates)
    elif _is_partition_blocks(partition):
        partish = [list(bloc) for bloc in partition]
    else:
        partish = backward_convert(np.asarray(partition), candidates)
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
