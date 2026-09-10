"""Check data selection and metric configuration shared by pipeline workflows."""

import json
from pathlib import Path

import pytest

from pipelines.bradley_terry import _metrics
from pipelines.scottish.plots._data import load_outputs_by_election_type


def test_scottish_loader_filters_before_reading_and_preserves_election_order(
    tmp_path: Path,
) -> None:
    for metric, tiebreak, contents in (
        ("sigma_IIA_average", "lex", {"7": {"election_z": 0.8, "election_a": 0.2}}),
        ("sigma_UM_worst_case_asin", "lex", {"7": {"election_z": 0.6, "election_a": 0.4}}),
        ("sigma_IIA_average", "random", None),
    ):
        folder = tmp_path / metric / "borda"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"METRIC_{metric}__ELECTION_TYPE_borda__TIEBREAK_{tiebreak}_output.json"
        path.write_text(json.dumps(contents) if contents else "not valid JSON")

    outputs = load_outputs_by_election_type(tmp_path, ["borda"], tiebreaks=("lex",))

    assert outputs == {
        "borda": {
            "7": {
                "sigma_IIA_average_lex": [0.8, 0.2],
                "sigma_UM_worst_case_asin_lex": [0.6, 0.4],
            }
        }
    }
    assert load_outputs_by_election_type(
        tmp_path, ["borda"], variants=("worst_case",), tiebreaks=("lex",)
    ) == {"borda": {"7": {"sigma_UM_worst_case_asin_lex": [0.6, 0.4]}}}


@pytest.mark.parametrize("metric_name", ["sigma_UM", "sigma_IIA_winner_set_all_subset"])
def test_configured_metrics_bind_interpolation_only_for_um(
    metric_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    received = []

    def metric(profile: str, rule: str, **options: str | int) -> float:
        received.append((profile, rule, options))
        return 0.75

    monkeypatch.setattr(_metrics, metric_name, metric)
    configured = _metrics.configure_metric(metric_name, 3, "average", "odds")

    assert configured("profile", "rule") == 0.75
    expected_options = {"n_seats": 3, "variant": "average"}
    if metric_name == "sigma_UM":
        expected_options["interpolation_type"] = "odds"

    assert received == [("profile", "rule", expected_options)]


def test_scottish_loader_treats_brackets_in_the_input_root_literally(tmp_path: Path) -> None:
    for name, score in (("run[1]", 0.1), ("run1", 0.9)):
        folder = tmp_path / name / "sigma_IIA_average/borda"
        folder.mkdir(parents=True)
        output = folder / "METRIC_sigma_IIA_average__ELECTION_TYPE_borda__TIEBREAK_lex_output.json"
        output.write_text(json.dumps({"7": {"election.csv": score}}))

    outputs = load_outputs_by_election_type(tmp_path / "run[1]", ["borda"], tiebreaks=("lex",))
    assert outputs == {"borda": {"7": {"sigma_IIA_average_lex": [0.1]}}}
