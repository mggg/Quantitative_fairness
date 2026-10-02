"""Shared candidate order, labels, and canvas sizing for Portland boost figures."""

from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

FOCUS_CANDIDATES: dict[str, tuple[list[str], list[str]]] = {
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


HEATMAP_SIZE_INCHES = 8.0
BOOST_COLORMAP = "PRGn"
SLATE_COLORS = ("#c35c1e", "#2A6FA1")

# Row-label and column-label sizes, in points.
LABEL_FONT_SIZES: dict[str, tuple[int, int]] = {
    "D1": (18, 18),
    "D2": (14, 18),
    "D3": (20, 20),
    "D4": (14, 18),
}


def set_candidate_labels(ax: Axes, slates: Sequence[Sequence[str]], district: str) -> None:
    """Apply the district's candidate labels and typography to heatmap axes.

    Args:
        ax (Axes): Axes with one unit per candidate on each dimension.
        slates (Sequence[Sequence[str]]): Ordered candidate groups.
        district (str): District whose row and column font sizes to use.
    """
    candidates = [candidate for slate in slates for candidate in slate]
    positions = np.arange(len(candidates)) + 0.5
    ax.set_xticks(positions, labels=[" ".join(name.split()[1:]) for name in candidates])
    ax.set_yticks(positions, labels=candidates, verticalalignment="center")
    ax.set_xlim(0, len(candidates))
    ax.set_ylim(len(candidates), 0)
    ax.tick_params(length=0, pad=8)
    ax.xaxis.set_ticks_position("top")
    row_fontsize, column_fontsize = LABEL_FONT_SIZES[district]

    for labels, fontsize, rotation in (
        (ax.get_yticklabels(), row_fontsize, 0),
        (ax.get_xticklabels(), column_fontsize, 45),
    ):
        for index, label in enumerate(labels):
            label.set_color(SLATE_COLORS[0] if index < len(slates[0]) else SLATE_COLORS[1])
            label.set_fontweight("bold")
            label.set_fontsize(fontsize)
            label.set_rotation(rotation)

    for label in ax.get_xticklabels():
        label.set_horizontalalignment("left")


def measure_heatmap_margins(
    slates: Sequence[Sequence[str]], district: str, dpi: float = 300
) -> tuple[float, float, float, float]:
    """Measure left, bottom, right, and top margins in inches for all district labels.

    Args:
        slates (Sequence[Sequence[str]]): Candidate groups used in this figure.
        district (str): District represented by this figure.
        dpi (float, optional): Resolution used to measure labels. Defaults to 300.

    Returns:
        tuple[float, float, float, float]: Left, bottom, right, and top margins in inches,
            including 0.1 inch of outer padding.
    """
    heatmap_size = HEATMAP_SIZE_INCHES
    margins = np.zeros(4)
    measurement = plt.figure(figsize=(heatmap_size, heatmap_size), dpi=dpi, layout="none")

    try:
        labels_ax = measurement.add_axes((0, 0, 1, 1))
        for label_district, label_slates in {**FOCUS_CANDIDATES, district: slates}.items():
            set_candidate_labels(labels_ax, label_slates, label_district)
            measurement.draw_without_rendering()
            bounds = measurement.get_tightbbox()
            margins = np.maximum(
                margins,
                [-bounds.x0, -bounds.y0, bounds.x1 - heatmap_size, bounds.y1 - heatmap_size],
            )
    finally:
        plt.close(measurement)

    left, bottom, right, top = margins + 0.1
    return float(left), float(bottom), float(right), float(top)


def fit_heatmap_canvas(
    fig: Figure, ax: Axes, slates: Sequence[Sequence[str]], district: str
) -> None:
    """Fit shared district-label margins around an 8-inch heatmap without scaling it.

    Args:
        fig (Figure): Heatmap figure to resize.
        ax (Axes): Heatmap axes to position within the resized canvas.
        slates (Sequence[Sequence[str]]): Candidate groups used in this figure.
        district (str): District represented by this figure.
    """
    heatmap_size = HEATMAP_SIZE_INCHES
    left, bottom, right, top = measure_heatmap_margins(slates, district, dpi=fig.dpi)
    width, height = heatmap_size + left + right, heatmap_size + bottom + top
    fig.set_size_inches(width, height)
    ax.set_position((left / width, bottom / height, heatmap_size / width, heatmap_size / height))
