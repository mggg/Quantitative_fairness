"""Render Portland focus-candidate boost heatmaps and export the underlying matrices."""

import argparse
import hashlib
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Sequence, cast

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure
from numpy.typing import NDArray
from votekit import RankProfile
from votekit.matrices import boost_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.portland.plots._boost_style import (
    BOOST_COLORMAP,
    FOCUS_CANDIDATES,
    HEATMAP_SIZE_INCHES,
    fit_heatmap_canvas,
    set_candidate_labels,
)
from voting_metrics_main_code.replication import ROOT


def plot_boost(
    slates: Sequence[Sequence[str]],
    district: str,
    profile: RankProfile | None = None,
    matrix: NDArray | None = None,
    limit: float = 0.21,
    matrix_savepath: Path | None = None,
) -> tuple[Figure, NDArray]:
    """Keep the full electorate, ordering focus candidates by the two slates.

    The heatmap occupies an 8-inch square. Shared margins accommodate all districts' labels
    at their configured font sizes, plus 0.1 inch of outer padding. Save the full canvas to
    preserve the same margins and physical scale across districts.

    Args:
        slates (Sequence[Sequence[str]]): Two ordered groups of focus candidate names.
        district (str): Portland district identifier.
        profile (RankProfile | None, optional): Ranked-ballot profile used to compute boosts.
            Provide this or matrix. Defaults to None.
        matrix (NDArray | None, optional): Precomputed boosts in flattened slate order. Provide this
            or profile. Defaults to None.
        limit (float, optional): Positive magnitude of the symmetric color scale. Defaults to 0.21.
        matrix_savepath (Path | None, optional): Cache destination for a computed boost matrix; an
            existing cache may be replaced. Defaults to None.

    Returns:
        tuple[Figure, NDArray]: Heatmap figure and boost matrix in flattened slate order.

    Raises:
        ValueError: Both or neither input is provided, a focus candidate is absent from the
            profile, or the matrix dimensions do not match the focus candidates.
    """
    if profile is None and matrix is None:
        raise ValueError("Either a profile or a matrix must be provided.")

    if profile is not None and matrix is not None:
        raise ValueError("Provide either a profile or a matrix, not both.")

    candidates = [candidate for slate in slates for candidate in slate]

    if profile is not None:
        missing = set(candidates) - set(profile.candidates)

        if missing:
            raise ValueError(f"Focus candidates missing from the profile: {sorted(missing)}")

        matrix = boost_matrix(profile, candidates=candidates)
        if matrix_savepath is not None:
            np.save(matrix_savepath, matrix)

    elif matrix is not None and (
        len(candidates) != matrix.shape[1] or len(candidates) != matrix.shape[0]
    ):
        raise ValueError(
            f"Number of focus candidates ({len(candidates)}) does not match matrix size ({matrix.shape[1]})"
        )

    assert matrix is not None, "Matrix should be defined at this point"

    fig = plt.figure(figsize=(HEATMAP_SIZE_INCHES, HEATMAP_SIZE_INCHES), dpi=300, layout="none")
    ax = fig.add_axes((0, 0, 1, 1))
    ax = sns.heatmap(
        matrix,
        ax=ax,
        cmap=BOOST_COLORMAP,
        vmin=-limit,
        vmax=limit,
        center=0,
        cbar=False,
        square=True,
        linewidths=1,
        xticklabels=False,
        yticklabels=False,
    )
    ax.set_facecolor("white")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)

    separator_color = "black"
    sep_width = 6
    ax.axvline(len(slates[0]), color=separator_color, linewidth=sep_width)
    ax.axhline(len(slates[0]), color=separator_color, linewidth=sep_width)

    set_candidate_labels(ax, slates, district)
    fit_heatmap_canvas(fig, ax, slates, district)

    return fig, matrix


def plot_colorbar(limit: float = 0.21) -> Figure:
    """Render the separate, centered boost color scale.

    Args:
        limit (float, optional): Positive magnitude of the symmetric color scale. Defaults to 0.21.

    Returns:
        Figure: Figure containing the standalone colorbar.

    Raises:
        ValueError: The color scale limit is not strictly positive.
    """
    fig, ax = plt.subplots(figsize=(0.5, HEATMAP_SIZE_INCHES))
    bar = fig.colorbar(
        plt.cm.ScalarMappable(
            norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), cmap=BOOST_COLORMAP
        ),
        cax=ax,
    )
    ticks = np.arange(-0.2, 0.25, 0.10) if limit == 0.21 else np.linspace(-limit, limit, 9)
    bar.set_ticks(
        ticks.tolist(),
        # Ternary to fix the negative sign on 0
        labels=[f"{0:.1f}" if tick == 0 else f"{tick:.1f}" for tick in ticks],
        fontsize=18,
    )

    return fig


def save_boost_matrix_csv(
    matrix: NDArray[np.float64], slates: Sequence[Sequence[str]], destination: Path
) -> None:
    """Write unrounded boosts with candidate order and slate membership.

    Args:
        matrix (NDArray[np.float64]): Square boost matrix in flattened slate order.
        slates (Sequence[Sequence[str]]): Ordered candidate groups matching the matrix axes.
        destination (Path): CSV file to write or replace; its parent directory must exist.
    """
    candidates = [candidate for slate in slates for candidate in slate]
    matrix_index = pd.MultiIndex.from_tuples(
        [
            (slate_index, candidate)
            for slate_index, slate in enumerate(slates, 1)
            for candidate in slate
        ],
        names=["Slate", "Candidate"],
    )

    pd.DataFrame(matrix, index=matrix_index, columns=candidates).to_csv(destination)


def main() -> None:
    """Save district heatmaps, a shared colorbar, and unrounded boost-matrix CSVs.

    Raises:
        SystemExit: Command-line parsing fails or the limit is invalid.
        ValueError: A focus candidate is absent from a selected profile.
        FileNotFoundError: A selected district profile CSV does not exist.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--district", choices=[*FOCUS_CANDIDATES, "all"], default="D3")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--cache-dir", type=Path, help="Reuse matrices matched to input contents")
    parser.add_argument("--limit", type=float, default=0.21)
    args = parser.parse_args()

    if not np.isfinite(args.limit) or args.limit <= 0:
        parser.error("--limit must be finite and positive")

    output = args.output_dir.resolve() / "plots/portland/boost_matrix"
    matrix_output = args.output_dir.resolve() / "stats/portland_boost_matrices"
    data = args.data_dir.resolve()

    output.mkdir(parents=True, exist_ok=True)
    matrix_output.mkdir(parents=True, exist_ok=True)
    districts = FOCUS_CANDIDATES if args.district == "all" else [args.district]

    for district in districts:
        profile_path = data / f"Portland_{district}_cleaned_votekit.csv"
        matrix_savepath = None
        if args.cache_dir is not None:
            with profile_path.open("rb") as source:
                profile_digest = hashlib.file_digest(source, "sha256").hexdigest()
            identity = repr((profile_digest, FOCUS_CANDIDATES[district], version("votekit")))
            cache_key = hashlib.sha256(identity.encode()).hexdigest()
            args.cache_dir.mkdir(parents=True, exist_ok=True)
            matrix_savepath = args.cache_dir / f"boost_matrix_{district}_{cache_key}.npy"

        print(f"Input profile: {profile_path}")
        if matrix_savepath is not None and matrix_savepath.exists():
            print(f"Loading matched cache: {matrix_savepath}")
            matrix = np.load(matrix_savepath)
            fig, matrix = plot_boost(
                FOCUS_CANDIDATES[district], district, matrix=matrix, limit=args.limit
            )
        else:
            profile = cast(RankProfile, RankProfile.from_csv(profile_path))
            fig, matrix = plot_boost(
                FOCUS_CANDIDATES[district],
                district,
                profile=profile,
                limit=args.limit,
                matrix_savepath=matrix_savepath,
            )

        save_boost_matrix_csv(
            matrix, FOCUS_CANDIDATES[district], matrix_output / f"boost_matrix_{district}.csv"
        )

        print(
            f"Saving boost matrix heatmap for {district} to {output / f'boost_matrix_{district}.png'}"
        )
        fig.savefig(output / f"boost_matrix_{district}.png", dpi=300, bbox_inches=fig.bbox_inches)
        plt.close(fig)

    fig = plot_colorbar(args.limit)

    fig.savefig(output / "boost_matrix_colorbar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
