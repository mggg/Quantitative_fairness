"""Check boost projection and modularity against hand-calculated matrices."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from votekit import RankBallot, RankProfile

from pipelines.portland.clustering import load_profile
from pipelines.portland.clustering.modularity import boost_modularity_matrix


def test_modularity_score_4x4() -> None:
    test_matrix = np.array([[0, 5, -5, -2], [2, 0, -10, 0], [-10, -1, 0, 12], [-3, 0, 6, 0]])

    test_mod_matrix = boost_modularity_matrix(test_matrix, np.array([0, 0, 1, 1]))

    assert test_mod_matrix[0, 1] == 5 - (5 * 5 / 25) + (7 * 1 / 31)
    assert test_mod_matrix[1, 0] == 2 - (2 * 2 / 25) + (10 * 13 / 31)
    assert test_mod_matrix[2, 3] == 12 - (12 * 12 / 25) + (11 * 2 / 31)
    assert test_mod_matrix[3, 2] == 6 - (6 * 6 / 25) + (3 * 15 / 31)


@pytest.fixture
def ranked_profile() -> RankProfile:
    return RankProfile(
        ballots=(
            RankBallot(ranking=(frozenset({"A"}), frozenset({"B"})), weight=3),
            RankBallot(ranking=(frozenset({"B"}), frozenset({"C"})), weight=2),
        ),
        candidates=("A", "B", "C"),
    )


def test_projected_boost_matches_hand_calculated_values(
    ranked_profile: RankProfile,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ranked_profile.to_csv(tmp_path / "Portland_D1_cleaned_votekit.csv")
    monkeypatch.setattr(
        load_profile, "FastSTV", lambda *args, **kwargs: SimpleNamespace(threshold=0)
    )

    projected, boost = load_profile.load_projected_profile(1, data_root=tmp_path)

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


def test_short_burst_search_uses_only_its_supplied_rng() -> None:
    import random

    from pipelines.portland.clustering.modularity import run_modularity_maximization_short_bursts

    matrix = np.array([[0, 5, -5, -2], [2, 0, -10, 0], [-10, -1, 0, 12], [-3, 0, 6, 0]])
    initial = np.array([0, 0, 1, 1])
    np.random.seed(1)
    expected, expected_score = run_modularity_maximization_short_bursts(
        matrix, initial, 2, 5, 20, random.Random(7)
    )
    assert np.random.random() == np.random.RandomState(1).random_sample()

    np.random.seed(999)
    actual, score = run_modularity_maximization_short_bursts(
        matrix, initial, 2, 5, 20, random.Random(7)
    )

    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(initial, [0, 0, 1, 1])
    assert score == expected_score
    assert set(actual) == {0, 1}


def test_restart_verification_compares_partitions_independently_of_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.portland.clustering import run_short_bursts as workflow

    result = workflow.ClusteringResult(
        np.array([0, 0, 1, 1, 2, 2]), 0.5, np.zeros((6, 6)), list("ABCDEF")
    )
    monkeypatch.setattr(workflow, "tqdm", lambda values: values)
    monkeypatch.setattr(
        workflow,
        "run_modularity_maximization_short_bursts",
        lambda *args, **kwargs: (np.array([2, 2, 0, 0, 1, 1]), 0.5),
    )
    workflow.verify_clustering_stability(result, n_clusters=3, burst_length=1, n_bursts=1)

    monkeypatch.setattr(
        workflow,
        "run_modularity_maximization_short_bursts",
        lambda *args, **kwargs: (np.array([2, 0, 2, 0, 1, 1]), 0.5),
    )
    with pytest.raises(RuntimeError, match="different partition"):
        workflow.verify_clustering_stability(result, n_clusters=3, burst_length=1, n_bursts=1)
