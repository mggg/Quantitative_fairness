"""Check Portland boost plotting through the command-line workflow."""

import sys

import matplotlib.pyplot as plt
import pytest
from votekit import RankBallot, RankProfile

from pipelines.portland.plots import plot_boost_matrix


@pytest.mark.parametrize("limit", [0.21, 0.3])
def test_boost_cli_loads_ranked_profile_and_saves_both_figures(tmp_path, monkeypatch, limit):
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
    finally:
        plt.close("all")
