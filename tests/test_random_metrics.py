"""Check random metrics and reproducibility across worker counts and resumed runs."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from votekit import RankBallot, RankProfile

from voting_metrics_main_code.replication import ROOT


def test_random_iia_uses_profile_candidates_and_repeats_with_seed() -> None:
    from voting_metrics_main_code.fairness_metric import (
        sigma_IIA_random,
        sigma_IIA_winner_set_random,
    )
    from voting_metrics_main_code.voting_rules import build_voting_rule, random_candidate_order

    profile = RankProfile(
        ballots=(
            RankBallot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}]))),
            RankBallot(ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"B"}, {"A"}]))),
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

    expanded_profile = RankProfile(
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
    first_order = random_candidate_order(cast(RankProfile, first))
    random.seed(10)
    assert random_candidate_order(cast(RankProfile, second)) == first_order


def test_bt_random_results_do_not_depend_on_worker_count_or_resume(tmp_path: Path) -> None:
    folder = (
        tmp_path / "02_02" / ("b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)")
    )
    folder.mkdir(parents=True)
    profile = RankProfile(
        ballots=(
            RankBallot(ranking=tuple(frozenset({c}) for c in "ABCD"), weight=3),
            RankBallot(ranking=tuple(frozenset({c}) for c in "DCBA"), weight=2),
        )
    )
    for index in range(3):
        profile.to_csv(folder / f"profile_{index}.csv")
    settings = tmp_path / "settings.txt"
    settings.write_text(str(folder) + "\n")

    def run(output: Path, workers: int) -> dict[Path, list[float]]:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipelines/bradley_terry/collect_metrics.py"),
                "--settings-file",
                str(settings),
                "--election-type",
                "random",
                "--n-seats",
                "2",
                "--profile-batch-size",
                "1",
                "--n-jobs",
                str(workers),
                "--output-dir",
                str(output),
                "--seed",
                "42",
            ],
            env={
                **os.environ,
                "PYTHONHASHSEED": "0",
            },
            check=True,
            capture_output=True,
        )
        return {
            path.relative_to(output): json.loads(path.read_text())
            for path in output.rglob("*.json")
        }

    serial = run(tmp_path / "serial", 1)
    parallel = run(tmp_path / "parallel", 2)
    assert len(serial) == 4
    assert serial == parallel
    regenerated = tmp_path / "parallel" / next(iter(parallel))
    regenerated.unlink()
    assert run(tmp_path / "parallel", 2) == serial
