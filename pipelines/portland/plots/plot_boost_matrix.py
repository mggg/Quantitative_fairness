"""Render Portland focus-candidate boost heatmaps and their separate colorbar."""

import argparse
import sys
from pathlib import Path
from typing import Sequence, cast

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
import seaborn as sns
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure
from votekit import RankProfile
from votekit.matrices import boost_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.replication import DATA_DIR, PLOTS_DIR, ROOT

CACHE_DIR = ROOT / ".boost_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


FOCUS_CANDIDATES = {
    "D1": (
        ["Candace Avalos", "Steph Routh", "Jamie Dunphy", "Timur Ender"],
        ["Loretta Smith", "Terrence Hayes", "Noah Ernst"],
    ),
    "D2": (
        ["Elana Pirtle-Guiney", "Dan Ryan", "Tiffani Penson", "Mariah Hudson"],
        ["Michelle DePass", "Sameer Kanal", "Nat West", "Jonathan Tasini", "Marnie Glickman"],
    ),
    "D3": (
        ["Angelita Morillo", "Tiffany Koyama Lane"],
        ["Steve Novick", "Jesse Cornett", "Rex Burkholder"],
    ),
    "D4": (
        ["Olivia Clark", "Eric Zimmerman", "Eli Arnold", "Bob Weinstein"],
        ["Mitch Green", "Sarah Silkie", "Chad Lykins", "Lisa Freeman"],
    ),
}


def plot_boost(
    slates: Sequence[Sequence[str]],
    profile: RankProfile | None = None,
    matrix: NDArray | None = None,
    limit: float = 0.21,
    matrix_savepath: Path | None = None,
) -> tuple[Figure, NDArray]:
    """Keep the full electorate, ordering focus candidates by the notebook's two slates.

    Args:
        slates (Sequence[Sequence[str]]): Two ordered groups of focus candidate names.
        profile (RankProfile | None, optional): Ranked-ballot profile used to compute boosts.
            Provide this or matrix. Defaults to None.
        matrix (NDArray | None, optional): Precomputed boosts in flattened slate order.
            Provide this or profile. Defaults to None.
        limit (float, optional): Positive magnitude of the symmetric color scale. Defaults to 0.21.
        matrix_savepath (Path | None, optional): Cache destination for a computed boost matrix;
            an existing cache may be replaced. Defaults to None.

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

    fig, ax = plt.subplots(figsize=(10, 10))
    sns.heatmap(
        matrix,
        ax=ax,
        cmap="PRGn",
        vmin=-limit,
        vmax=limit,
        center=0,
        cbar=False,
        square=True,
        linewidths=0,
        xticklabels=[" ".join(candidate.split()[1:]) for candidate in candidates],
        yticklabels=candidates,
    )
    ax.set_facecolor("white")
    ax.xaxis.set_ticks_position("top")

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)

    ax.axvline(len(slates[0]), color="black", linewidth=4)
    ax.axhline(len(slates[0]), color="black", linewidth=4)

    for labels in (ax.get_xticklabels(), ax.get_yticklabels()):
        for index, label in enumerate(labels):
            label.set_color("#FFA812" if index < len(slates[0]) else "#008080")
            label.set_fontweight("bold")
            label.set_fontsize(18)

    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment("left")

    for label in ax.get_yticklabels():
        label.set_rotation(0)

    return fig, matrix


def plot_colorbar(limit: float = 0.21) -> Figure:
    """Render the notebook's separate, centered color scale.

    Args:
        limit (float, optional): Positive magnitude of the symmetric color scale. Defaults to 0.21.

    Returns:
        Figure: Figure containing the standalone colorbar.

    Raises:
        ValueError: The color scale limit is not strictly positive.
    """
    fig, ax = plt.subplots(figsize=(0.5, 8))
    bar = fig.colorbar(
        plt.cm.ScalarMappable(norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit), cmap="PRGn"),
        cax=ax,
    )
    ticks = np.arange(-0.2, 0.25, 0.05) if limit == 0.21 else np.linspace(-limit, limit, 9)
    bar.set_ticks(ticks.tolist(), labels=[f"{tick:.2f}" for tick in ticks], fontsize=18)

    return fig


def main() -> None:
    """Save focus-candidate heatmaps for the selected Portland districts and a shared colorbar.

    Raises:
        SystemExit: Command-line parsing fails or the limit is invalid.
        ValueError: A focus candidate is absent from a selected profile.
        FileNotFoundError: A selected district profile CSV does not exist.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--district", choices=[*FOCUS_CANDIDATES, "all"], default="D3")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=PLOTS_DIR / "portland/boost_matrix")
    parser.add_argument("--limit", type=float, default=0.21)
    args = parser.parse_args()

    if not np.isfinite(args.limit) or args.limit <= 0:
        parser.error("--limit must be finite and positive")

    output = args.output_dir.resolve()
    data = args.data_dir.resolve()

    output.mkdir(parents=True, exist_ok=True)
    districts = FOCUS_CANDIDATES if args.district == "all" else [args.district]

    for district in districts:
        matrix_savepath = Path(CACHE_DIR / f"boost_matrix_Portland_{district}_boost.npy")
        if matrix_savepath.exists():
            print(f"Loading cached boost matrix for {district} from {matrix_savepath}")
            matrix = np.load(matrix_savepath)
            fig, _ = plot_boost(FOCUS_CANDIDATES[district], matrix=matrix, limit=args.limit)
        else:
            profile = cast(
                RankProfile, RankProfile.from_csv(data / f"Portland_{district}_cleaned_votekit.csv")
            )
            fig, _ = plot_boost(
                FOCUS_CANDIDATES[district],
                profile=profile,
                limit=args.limit,
                matrix_savepath=matrix_savepath,
            )

        print(
            f"Saving boost matrix heatmap for {district} to {output / f'boost_matrix_{district}.png'}"
        )
        fig.savefig(output / f"boost_matrix_{district}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    fig = plot_colorbar(args.limit)

    fig.savefig(output / "boost_matrix_colorbar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
