"""Check Portland boost plotting through the command-line workflow."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from votekit import RankBallot, RankProfile

from pipelines.portland.plots import plot_boost_matrix


@pytest.mark.parametrize("font_sizes", [(10, 12), (16, 18), (24, 30)])
def test_font_changes_resize_shared_canvas_without_scaling_heatmaps(
    monkeypatch: pytest.MonkeyPatch, font_sizes: tuple[int, int]
) -> None:
    monkeypatch.setitem(plot_boost_matrix.FONTSIZES, "D2", font_sizes)
    canvas_sizes = []
    outer_margins = []

    for district, slates in plot_boost_matrix.FOCUS_CANDIDATES.items():
        candidate_count = sum(map(len, slates))
        matrix = np.zeros((candidate_count, candidate_count))
        figure, _ = plot_boost_matrix.plot_boost(slates, district, matrix=matrix)

        try:
            figure.canvas.draw()
            axes = figure.axes[0]
            heatmap = axes.get_window_extent().transformed(figure.dpi_scale_trans.inverted())
            assert (heatmap.width, heatmap.height) == pytest.approx((8.0, 8.0))
            width, height = figure.get_size_inches()
            canvas_sizes.append((width, height))

            bounds = figure.get_tightbbox()
            margins = [bounds.x0, bounds.y0, width - bounds.x1, height - bounds.y1]
            assert min(margins) >= 0.09
            outer_margins.append(margins)
            row_size, column_size = plot_boost_matrix.FONTSIZES[district]
            assert all(label.get_fontsize() == row_size for label in axes.get_yticklabels())
            assert all(label.get_fontsize() == column_size for label in axes.get_xticklabels())
        finally:
            plt.close(figure)

    assert canvas_sizes == pytest.approx([canvas_sizes[0]] * 4)
    assert np.min(outer_margins, axis=0) == pytest.approx([0.1] * 4, abs=0.01)


@pytest.mark.parametrize("limit", [0.21, 0.3])
def test_boost_cli_loads_ranked_profile_and_saves_both_figures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: float
) -> None:
    candidates = [
        candidate for slate in plot_boost_matrix.FOCUS_CANDIDATES["D3"] for candidate in slate
    ]
    profile = RankProfile(
        ballots=(
            RankBallot(ranking=tuple(frozenset({name}) for name in candidates[:3]), weight=3),
            RankBallot(ranking=tuple(frozenset({name}) for name in candidates[2:]), weight=2),
        ),
        candidates=tuple(candidates),
    )
    data = tmp_path / "data"
    data.mkdir()
    profile.to_csv(data / "Portland_D3_cleaned_votekit.csv")
    output = tmp_path / "figures"
    output.mkdir()
    for name in ("boost_matrix_D3.png", "boost_matrix_colorbar.png"):
        (output / name).write_text("old figure")
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(plot_boost_matrix, "CACHE_DIR", cache)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "plot_boost_matrix.py",
            "--data-dir",
            str(data),
            "--output-dir",
            str(output),
            "--limit",
            str(limit),
        ],
    )

    try:
        plot_boost_matrix.main()
        assert {path.name for path in output.iterdir()} == {
            "boost_matrix_D3.png",
            "boost_matrix_colorbar.png",
        }
        for path in output.iterdir():
            assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        cached_matrix = np.load(cache / "boost_matrix_Portland_D3_boost.npy")
        reference, _ = plot_boost_matrix.plot_boost(
            plot_boost_matrix.FOCUS_CANDIDATES["D3"], "D3", matrix=cached_matrix
        )
        expected_width, expected_height = (reference.get_size_inches() * 300).astype(int)
        heatmap_image = plt.imread(output / "boost_matrix_D3.png")
        assert heatmap_image.shape[:2] == (expected_height, expected_width)
    finally:
        plt.close("all")
