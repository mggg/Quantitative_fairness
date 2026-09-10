"""Exercise runtime failures exposed by pipeline type checking."""

from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import pytest
from votekit import RankBallot, RankProfile

from pipelines.bradley_terry.alpha_sweep import collect_metrics, collect_metrics_borda_tiebreak
from pipelines.portland.clustering import run_brute_force, run_short_bursts
from pipelines.scottish.plots.plot_metric_boxplots import save_legend_only


@pytest.fixture
def ranked_profile():
    return RankProfile(
        ballots=(
            RankBallot(ranking=(frozenset({"A"}), frozenset({"B"})), weight=3),
            RankBallot(ranking=(frozenset({"B"}), frozenset({"C"})), weight=2),
        ),
        candidates=("A", "B", "C"),
    )


@pytest.mark.parametrize("collector", [collect_metrics, collect_metrics_borda_tiebreak])
def test_alpha_collector_loads_ranked_csv(collector, ranked_profile, tmp_path):
    path = tmp_path / "profile.csv"
    ranked_profile.to_csv(path)

    def metric(profile, rule):
        assert isinstance(profile, RankProfile)
        assert profile.candidates == ranked_profile.candidates
        assert rule == "selected rule"
        return profile.total_ballot_wt

    assert collector.run_score(path, metric, "selected rule") == 5


def test_short_burst_trivial_partition_returns_complete_result(monkeypatch, ranked_profile):
    boost = np.array([[0.0, 0.2, -0.1], [-0.3, 0.0, 0.1], [0.2, -0.1, 0.0]])
    monkeypatch.setattr(run_short_bursts, "load_and_project", lambda _: (ranked_profile, boost))

    assignment, score, returned_boost, candidates = (
        run_short_bursts.run_short_burst_for_portland_profile_i(1, n_clusters=3)
    )

    np.testing.assert_array_equal(assignment, [0, 1, 2])
    assert score == 0
    assert returned_boost is boost
    assert candidates == list(ranked_profile.candidates)


@pytest.mark.parametrize("workflow", [run_brute_force, run_short_bursts])
def test_projection_uses_boost_matrix_without_probability_matrices(
    workflow, ranked_profile, tmp_path, monkeypatch
):
    ranked_profile.to_csv(tmp_path / "Portland_D1_cleaned_votekit.csv")
    monkeypatch.setattr(workflow, "DATA_DIR", tmp_path)
    monkeypatch.setattr(workflow, "FastSTV", lambda *args, **kwargs: SimpleNamespace(threshold=0))

    projected, boost = workflow.load_and_project(1)

    assert set(projected.candidates) == set(ranked_profile.candidates)
    assert boost.shape == (3, 3)
    expected = {("A", "C"): -0.6, ("C", "A"): -0.4}
    np.testing.assert_allclose(
        boost,
        [
            [expected.get((first, second), 0.0) for second in projected.candidates]
            for first in projected.candidates
        ],
        atol=1e-15,
    )


@pytest.mark.parametrize("use_subfigure", [False, True])
def test_legend_export_uses_root_figure(tmp_path, use_subfigure):
    figure = plt.figure()
    parent = figure.subfigures() if use_subfigure else figure
    axes = parent.subplots()
    axes.plot([0, 1], [0.2, 0.8], label="Borda")
    legend = axes.legend()
    output = tmp_path / "legend.png"

    try:
        save_legend_only(legend, output, dpi=40)
        assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        plt.close(figure)
