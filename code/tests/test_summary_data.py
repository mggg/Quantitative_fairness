"""Check that summaries preserve election pairing and compute the intended dispersion."""

import json
from pathlib import Path

import pandas as pd

from pipelines.bradley_terry.plots._data import load_metric_samples, load_metric_summaries
from pipelines.scottish.plots._data import (
    build_boxplot_table,
    export_aggregate_tables,
    load_outputs_by_election_type,
)


def test_boxplot_tables_preserve_requested_order_and_missing_observations() -> None:
    outputs = {
        "stv": {"7": {"metric": [0.8]}, "6": {"metric": [0.9]}},
        "borda": {"7": {"metric": [0.4, 0.2]}, "6": {"metric": [0.6]}},
    }

    metric_values_df = build_boxplot_table(outputs, [7, 6], "metric")
    expected_df = pd.DataFrame(
        {
            "rule": ["stv", "stv", "borda", "borda", "stv", "borda"],
            "value": [0.8, float("nan"), 0.4, 0.2, 0.9, 0.6],
            "n_cands": [7, 7, 7, 7, 6, 6],
        }
    )

    pd.testing.assert_frame_equal(metric_values_df, expected_df)
    pd.testing.assert_frame_equal(
        build_boxplot_table(outputs, [7, 6], "metric", borda_only=True),
        expected_df[expected_df["rule"] == "borda"].reset_index(drop=True),
    )


def test_aggregate_exports_preserve_rule_order_and_mark_missing_counts(tmp_path: Path) -> None:
    stats_dir = tmp_path / "saved"
    stats_dir.mkdir()
    (stats_dir / "borda_stats.json").write_text(json.dumps({"6": {"mean": 0.4}}))
    (stats_dir / "stv_stats.json").write_text(json.dumps({"6": {"mean": 0.8}}))

    export_aggregate_tables(
        stats_dir, ["stv", "borda"], [7, 6], "average", "lex", output_root=tmp_path
    )
    statistics_df = pd.read_csv(tmp_path / "stats/scottish_stats/scottish_stats_average_lex.csv")
    expected_df = pd.DataFrame(
        {
            "rule": ["stv", "stv", "borda", "borda"],
            "n_cands": [7, 6, 7, 6],
            "mean": [float("nan"), 0.8, float("nan"), 0.4],
        }
    )

    pd.testing.assert_frame_equal(statistics_df, expected_df)


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
