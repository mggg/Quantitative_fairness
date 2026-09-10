import json
import random
import runpy
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from click.testing import CliRunner
from votekit import RankBallot as Ballot
from votekit import RankProfile as PreferenceProfile

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "pipelines/bradley_terry/collect_metrics.py")
)


def test_output_jobs_preserve_run_and_retry_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_folder = (
        tmp_path / "02_06" / "b_proportion_0.5__ALPHA_(0.50,1.00,0.50,1.00)__COHESION_(0.70,0.90)"
    )

    input_folder.mkdir(parents=True)
    (input_folder / "profile_0.csv").touch()
    _, jobs = MODULE["output_jobs"](input_folder, 3, "random", "lex", output_root=tmp_path)

    assert len(jobs) == 4
    assert {job[-1].parts[-4] for job in jobs} == {
        "sigma_UM",
        "sigma_UM_winner_set",
        "sigma_IIA",
        "sigma_IIA_winner_set",
    }
    for *_, output_file in jobs:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.touch()
    settings_file = tmp_path / "settings.txt"
    settings_file.write_text(str(input_folder))

    result = CliRunner().invoke(
        MODULE["main"], ["--settings-file", str(settings_file), "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "Skipping 4 completed folder/metric outputs." in result.output
    assert "All outputs already exist." in result.output


def test_profile_batch_loads_each_profile_once_for_multiple_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = []

    class FakeRankProfile:
        @staticmethod
        def from_csv(path: Path) -> int:
            loaded.append(path)
            return int(path.stem)

    def metric(
        profile: int, voting_rule: str, n_seats: int, variant: str, interpolation_type: str
    ) -> int:
        assert voting_rule == "rule"
        assert variant == "worst_case"
        assert interpolation_type == "asin"
        return profile + n_seats

    run_profile_batch = MODULE["run_profile_batch"]
    monkeypatch.setitem(run_profile_batch.__globals__, "RankProfile", FakeRankProfile)
    monkeypatch.setitem(
        run_profile_batch.__globals__,
        "build_voting_rule",
        lambda *args, **kwargs: "rule",
    )

    profile_batch = ((2, tmp_path / "2.csv"), (5, tmp_path / "5.csv"))
    result = run_profile_batch(
        profile_batch,
        8,
        3,
        "random",
        "lex",
        (
            (7, metric, "worst_case", "asin"),
            (9, metric, "worst_case", "asin"),
        ),
    )

    expected_scores = ((2, 5), (5, 8))
    assert result == ((7, expected_scores), (9, expected_scores))
    assert loaded == [tmp_path / "2.csv", tmp_path / "5.csv"]


def test_random_iia_fast_paths_are_profile_based_and_deterministic_when_seeded() -> None:
    from voting_metrics_main_code.fairness_metric import (
        sigma_IIA_random,
        sigma_IIA_winner_set_random,
    )
    from voting_metrics_main_code.voting_rules import build_voting_rule, random_candidate_order

    profile = PreferenceProfile(
        ballots=(
            Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}]))),
            Ballot(ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"B"}, {"A"}]))),
        )
    )
    voting_rule = build_voting_rule(4, "random")

    for seed in range(5):
        for variant in ("average", "worst_case"):
            random.seed(seed)
            expected = sigma_IIA_random(profile, voting_rule, 2, variant=variant)
            random.seed(seed)
            assert sigma_IIA_random(profile, voting_rule, 2, variant=variant) == expected

            random.seed(seed)
            expected = sigma_IIA_winner_set_random(profile, voting_rule, 2, variant=variant)
            random.seed(seed)
            assert sigma_IIA_winner_set_random(profile, voting_rule, 2, variant=variant) == expected

    expanded_profile = PreferenceProfile(
        ballots=profile.ballots,
        candidates=(*profile.candidates, "E"),
    )
    expanded_rule = build_voting_rule(5, "random")
    random.seed(0)
    original_score = sigma_IIA_random(profile, voting_rule, 2)
    random.seed(0)
    expanded_score = sigma_IIA_random(expanded_profile, expanded_rule, 2)
    assert expanded_score != original_score

    first = SimpleNamespace(candidates=("A", "B", "C"), candidates_cast=("C", "A", "B"))
    second = SimpleNamespace(candidates=("C", "B", "A"), candidates_cast=("B", "C", "A"))
    random.seed(10)
    first_order = random_candidate_order(cast(PreferenceProfile, first))
    random.seed(10)
    assert random_candidate_order(cast(PreferenceProfile, second)) == first_order


def test_write_scores_publishes_complete_results_without_replacing_them(tmp_path: Path) -> None:
    output_file = tmp_path / "scores.json"

    MODULE["write_scores"](output_file, [0.2, 0.8])

    assert json.loads(output_file.read_text()) == [0.2, 0.8]
    with pytest.raises(FileExistsError, match="manually"):
        MODULE["write_scores"](output_file, [0.9])

    assert json.loads(output_file.read_text()) == [0.2, 0.8]
    assert list(tmp_path.iterdir()) == [output_file]
