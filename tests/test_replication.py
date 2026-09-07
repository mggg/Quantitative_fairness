"""Regression checks for preservation, portable inputs, and independent random streams."""

import io
import json
import os
import runpy
import subprocess
import sys
import tarfile

import pytest
from votekit import RankBallot, RankProfile

from voting_metrics_main_code.replication import ROOT, check_output_directory


def test_output_paths_cannot_overlap_preserved_files(tmp_path):
    for name in ("data", "stats", "plots", "paper", "dev_files", "notebooks", "other_files"):
        with pytest.raises(ValueError):
            check_output_directory(ROOT / name / "new-output")
    with pytest.raises(ValueError):
        check_output_directory(ROOT)
    alias = tmp_path / "alias"
    alias.symlink_to(ROOT / "stats", target_is_directory=True)
    with pytest.raises(ValueError):
        check_output_directory(alias / "new-output")
    assert check_output_directory(tmp_path / "new") == tmp_path / "new"


@pytest.mark.parametrize("directory_link", [True, False])
def test_nested_output_symlinks_are_rejected(tmp_path, directory_link):
    output = tmp_path / "output"
    nested = output / "stats/ny_stats"
    nested.mkdir(parents=True)
    target = (
        ROOT / "stats/ny_stats" if directory_link else ROOT / "data/NY_mayor_cleaned_votekit.csv"
    )
    (nested / "alias").symlink_to(target, target_is_directory=directory_link)
    with pytest.raises(ValueError, match="symlink"):
        check_output_directory(output)


def test_archive_extraction_preserves_existing_data_and_rejects_bad_paths(tmp_path):
    extract = runpy.run_path(ROOT / "scripts/fetch_data.py")["extract_profiles"]
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


def test_bt_rejects_missing_profiles_without_writing_results(tmp_path):
    settings = tmp_path / "settings.txt"
    settings.write_text("data/does-not-exist\n")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipelines/bradley-terry/collect_stats_final_set_v2.py"),
            "--settings-file",
            str(settings),
        ],
        env={**os.environ, "QF_RESULTS_DIR": str(tmp_path / "output")},
        capture_output=True,
    )
    assert result.returncode != 0
    assert b"Missing or empty profile folder" in result.stderr
    assert not (tmp_path / "output").exists()


def test_bt_random_results_do_not_depend_on_worker_count_or_resume(tmp_path):
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

    def run(output, workers):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipelines/bradley-terry/collect_stats_final_set_v2.py"),
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


def test_smoke_example():
    runpy.run_path(ROOT / "scripts/smoke_test.py")["main"]()


def test_generated_profiles_and_utilities_are_seeded_and_never_replaced(tmp_path):
    generate = runpy.run_path(ROOT / "pipelines/bradley-terry/generate_BT_profiles.py")[
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


def test_consolidated_metrics_match_both_deterministic_baselines(monkeypatch):
    from voting_metrics_main_code import fairness_metric, voting_rules
    from voting_metrics_main_code.voting_rules import build_voting_rule

    # The preserved root implementation imports voting_rules by its historical module name.
    with monkeypatch.context() as historical_imports:
        historical_imports.setitem(sys.modules, "voting_rules", voting_rules)
        originals = [
            runpy.run_path(ROOT / "archive/pre_cleanup" / name)
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
