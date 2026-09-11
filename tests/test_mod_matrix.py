"""Check boost projection and modularity against hand-calculated matrices."""

from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from votekit import RankBallot, RankProfile

from pipelines.portland.clustering import run_brute_force, run_short_bursts
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


@pytest.mark.parametrize("workflow", [run_brute_force, run_short_bursts])
def test_projected_boost_matches_hand_calculated_values(
    workflow: ModuleType,
    ranked_profile: RankProfile,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ranked_profile.to_csv(tmp_path / "Portland_D1_cleaned_votekit.csv")
    monkeypatch.setattr(workflow, "FastSTV", lambda *args, **kwargs: SimpleNamespace(threshold=0))

    projected, boost = workflow.load_and_project(1, data_root=tmp_path)

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
