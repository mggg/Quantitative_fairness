"""Check that summaries preserve election pairing and compute the intended dispersion."""

import json
from pathlib import Path

from pipelines.bradley_terry.plots._data import load_metric_samples, load_metric_summaries
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


def test_metric_loaders_preserve_file_and_observation_order(tmp_path: Path) -> None:
    first = tmp_path / "z.json"
    second = tmp_path / "a.json"
    first.write_text("[3, 1]")
    second.write_text("[8, 4]")
    paths = [str(first), str(second)]

    assert load_metric_samples(paths) == [3, 1, 8, 4]
    assert load_metric_summaries(paths) == [[2.0, 1.0], [6.0, 2.0]]
    assert load_metric_summaries(paths, "var") == [[2.0, 1.0], [6.0, 4.0]]
