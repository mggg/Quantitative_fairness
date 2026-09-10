"""Regression checks for preservation, portable inputs, and independent random streams."""

import io
import json
import os
import runpy
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from votekit import RankBallot, RankProfile

from voting_metrics_main_code.replication import ROOT, new_data_file


@pytest.mark.parametrize("destination_kind", ["file", "symlink", "dangling_symlink"])
def test_data_files_require_manual_removal_before_replacement(
    tmp_path: Path, destination_kind: str
) -> None:
    original = tmp_path / "original.json"
    original.write_text("preserved")
    destination = original
    if destination_kind != "file":
        destination = tmp_path / "result.json"
        destination.symlink_to(
            original if destination_kind == "symlink" else tmp_path / "missing.json"
        )

    with pytest.raises(FileExistsError, match="manually"):
        with new_data_file(destination) as temporary:
            temporary.write_text("replacement")

    assert original.read_text() == "preserved"
    assert not (tmp_path / "missing.json").exists()


def test_data_publication_preserves_a_result_created_during_computation(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    with pytest.raises(FileExistsError, match="manually"):
        with new_data_file(destination) as temporary:
            temporary.write_text("this run")
            destination.write_text("concurrent run")

    assert destination.read_text() == "concurrent run"
    assert list(tmp_path.iterdir()) == [destination]


def test_failed_data_writes_leave_no_partial_result(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    with pytest.raises(RuntimeError):
        with new_data_file(destination) as temporary:
            temporary.write_text("incomplete")
            raise RuntimeError("calculation failed")

    assert not list(tmp_path.iterdir())


def test_path_imports_allow_existing_output_trees_without_scanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "plots"
    output.mkdir()
    (output / "alias").symlink_to(ROOT / "data", target_is_directory=True)
    monkeypatch.setenv("QF_RESULTS_DIR", str(output))
    monkeypatch.setattr(os, "walk", lambda *args, **kwargs: pytest.fail("Unexpected tree scan"))

    paths = runpy.run_path(str(ROOT / "voting_metrics_main_code/replication.py"))

    assert paths["PLOTS_DIR"] == output / "plots"
    assert list(output.iterdir()) == [output / "alias"]


def test_archive_extraction_preserves_existing_data_and_rejects_bad_paths(tmp_path: Path) -> None:
    extract = runpy.run_path(str(ROOT / "scripts/fetch_data.py"))["extract_profiles"]
    archive = tmp_path / "profiles.tar.xz"
    with tarfile.open(archive, "w:xz") as handle:
        member = tarfile.TarInfo("preference_profiles/example.csv")
        member.size = 4
        handle.addfile(member, io.BytesIO(b"data"))
    destination = tmp_path / "profiles"
    extract(archive, destination)
    assert (destination / "example.csv").read_bytes() == b"data"
    with pytest.raises(FileExistsError):
        extract(archive, destination)
    assert (destination / "example.csv").read_bytes() == b"data"
    with tarfile.open(archive, "w:xz") as handle:
        handle.addfile(tarfile.TarInfo("preference_profiles/../../outside.csv"))
    with pytest.raises(ValueError):
        extract(archive, tmp_path / "another")
    assert not (tmp_path / "another").exists()
    assert not (tmp_path / "outside.csv").exists()


def test_bt_rejects_missing_profiles_without_writing_results(tmp_path: Path) -> None:
    settings = tmp_path / "settings.txt"
    settings.write_text("data/does-not-exist\n")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipelines/bradley_terry/collect_metrics.py"),
            "--settings-file",
            str(settings),
        ],
        env={**os.environ, "QF_RESULTS_DIR": str(tmp_path / "output")},
        capture_output=True,
    )
    assert result.returncode != 0
    assert b"Missing or empty profile folder" in result.stderr
    assert not (tmp_path / "output").exists()


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
            ],
            env={
                **os.environ,
                "QF_RESULTS_DIR": str(output),
                "QF_SEED": "42",
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


def test_smoke_example() -> None:
    runpy.run_path(str(ROOT / "scripts/smoke_test.py"))["main"]()


def test_generated_profiles_and_utilities_are_seeded_and_never_replaced(tmp_path: Path) -> None:
    generate = runpy.run_path(str(ROOT / "pipelines/bradley_terry/generate_profiles.py"))[
        "generate_and_save_profile"
    ]
    arguments = (2, 2, 40, 0.5, 0.7, 0.7, 1, 1, 1, 1, 0)
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(*arguments, str(first / "preference_profiles"))
    generate(*arguments, str(second / "preference_profiles"))
    expected = {p.relative_to(first): p.read_bytes() for p in first.rglob("*.csv")}
    assert len(expected) == 2
    assert expected == {p.relative_to(second): p.read_bytes() for p in second.rglob("*.csv")}
    with pytest.raises(FileExistsError):
        generate(*arguments, str(first / "preference_profiles"))
    assert expected == {p.relative_to(first): p.read_bytes() for p in first.rglob("*.csv")}


def test_preference_intervals_are_preserved_when_the_profile_has_been_moved(tmp_path: Path) -> None:
    generate = runpy.run_path(str(ROOT / "pipelines/bradley_terry/generate_profiles.py"))[
        "generate_and_save_profile"
    ]
    arguments = (2, 2, 40, 0.5, 0.7, 0.7, 1, 1, 1, 1)
    profiles = tmp_path / "preference_profiles"
    generate(*arguments, 0, str(profiles))
    profile = next(profiles.rglob("*.csv"))
    interval = next((tmp_path / "preference_dfs").rglob("*.csv"))
    contents = interval.read_bytes()
    profile.rename(tmp_path / "moved-profile.csv")

    with pytest.raises(FileExistsError, match="manually"):
        generate(*arguments, 0, str(profiles))

    assert not profile.exists()
    assert interval.read_bytes() == contents

    generate(*arguments, 1, str(profiles))
    assert len(list((tmp_path / "preference_dfs").rglob("*.csv"))) == 2


def test_consolidated_metrics_match_both_deterministic_baselines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from voting_metrics_main_code import fairness_metric, voting_rules
    from voting_metrics_main_code.voting_rules import build_voting_rule

    # The preserved root implementation imports voting_rules by its historical module name.
    with monkeypatch.context() as historical_imports:
        historical_imports.setitem(sys.modules, "voting_rules", voting_rules)
        originals = [
            runpy.run_path(str(ROOT / "archive/pre_cleanup" / name))
            for name in (
                "fairness_metric.py.txt",
                "voting_metrics_main_code/fairness_metric.py.txt",
            )
        ]
    profile = RankProfile(
        ballots=tuple(
            RankBallot(ranking=tuple(frozenset({c}) for c in ranking), weight=weight)
            for ranking, weight in (("ABCD", 5), ("BCDA", 3), ("DCAB", 2))
        )
    )
    for rule in ("borda", "plurality", "stv", "ranked-pairs"):
        constructor = build_voting_rule(4, rule, tiebreak="lex")
        for name in ("sigma_IIA", "sigma_IIA_winner_set", "sigma_UM", "sigma_UM_winner_set"):
            result = getattr(fairness_metric, name)(profile, constructor, n_seats=2)
            for original in originals:
                assert result == original[name](profile, constructor, n_seats=2)
