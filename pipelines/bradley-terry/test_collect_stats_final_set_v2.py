import json
import runpy
from pathlib import Path

from click.testing import CliRunner

MODULE = runpy.run_path(Path(__file__).with_name("collect_stats_final_set_v2.py"))


def test_output_jobs_preserve_run_and_retry_semantics(tmp_path, monkeypatch):
    input_folder = (
        tmp_path
        / "02_06"
        / "b_proportion_0.5__ALPHA_(0.50,1.00,0.50,1.00)__COHESION_(0.70,0.90)"
    )
    monkeypatch.setitem(MODULE["output_jobs"].__globals__, "PROJECT_ROOT", tmp_path)

    _, jobs = MODULE["output_jobs"](input_folder, 3, "random", "lex")

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

    result = CliRunner().invoke(MODULE["main"], ["--settings-file", str(settings_file)])

    assert result.exit_code == 0
    assert "Skipping 4 completed folder/metric outputs." in result.output
    assert "All outputs already exist." in result.output


def test_profile_batch_scores_keep_their_input_order(tmp_path, monkeypatch):
    class FakeRankProfile:
        @staticmethod
        def from_csv(path):
            return int(path.stem)

    def metric(profile, voting_rule, n_seats, variant, interpolation_type):
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

    result = run_profile_batch(
        7,
        ((2, tmp_path / "2.csv"), (5, tmp_path / "5.csv")),
        8,
        3,
        "random",
        "lex",
        metric,
        "worst_case",
        "asin",
    )

    assert result == (7, ((2, 5), (5, 8)))


def test_write_scores_is_atomic(tmp_path):
    output_file = tmp_path / "scores.json"

    MODULE["write_scores"](output_file, [0.2, 0.8])

    assert json.loads(output_file.read_text()) == [0.2, 0.8]
    assert not output_file.with_suffix(".json.tmp").exists()
