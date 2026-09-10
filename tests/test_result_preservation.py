"""Check that collectors reuse saved metrics without replacing or recomputing them."""

import importlib
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.mark.parametrize("dataset", ["new_york", "portland"])
def test_city_collectors_skip_saved_results_before_loading_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dataset: str
) -> None:
    collector = importlib.import_module(f"pipelines.{dataset}.collect_metrics")
    folder = tmp_path / "stats" / ("ny_stats" if dataset == "new_york" else "portland_stats")
    folder.mkdir(parents=True)
    for rule in ("borda", "3-approval", "2-approval", "plurality", "stv", "ranked-pairs"):
        (folder / f"{rule}_output.json").write_text("saved result")

    collector.main(data_root=tmp_path / "missing-inputs", output_root=tmp_path)

    assert [path.read_text() for path in folder.iterdir()] == ["saved result"] * 6


@pytest.mark.parametrize("tiebreak", ["lex", "borda"])
def test_alpha_collectors_skip_saved_results_before_parallel_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tiebreak: str
) -> None:
    collector = importlib.import_module("pipelines.bradley_terry.alpha_sweep.collect_metrics")
    folder = tmp_path / "stats/bt_profile_stats/1_seats/sigma_UM/04/alpha_0.50"
    folder.mkdir(parents=True)
    output = folder / (
        "METRIC_sigma_UM__SEATS_1__NCANDS_4__ALPHA_0.50__TYPE_borda"
        f"__VARIANT_worst_case__TIEBREAK_{tiebreak}__INTERP_asin.json"
    )
    output.write_text("saved result")
    monkeypatch.setattr(collector, "Parallel", lambda **kwargs: pytest.fail("Recomputed result"))

    result = CliRunner().invoke(
        collector.main,
        [
            "--output-dir",
            str(tmp_path),
            "--n-cands",
            "4",
            "--alpha-value",
            "0.50",
            "--metric",
            "sigma_UM",
            "--variant",
            "worst_case",
            "--election-type",
            "borda",
            "--tiebreak",
            tiebreak,
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.read_text() == "saved result"


def test_proportionality_skips_saved_results_before_loading_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipelines.bradley_terry import compute_proportionality as collector

    folder = tmp_path / "stats/bt_proportionality"
    folder.mkdir(parents=True)
    output = folder / "02_02_bprop_0.5_cohesion_(0.70,0.70)_results.json"
    output.write_text("saved result")
    monkeypatch.setattr(
        collector, "get_all_profiles", lambda *args: pytest.fail("Recomputed result")
    )

    result = CliRunner().invoke(
        collector.main,
        [
            "--output-dir",
            str(tmp_path),
            "--n-a-cand",
            "2",
            "--n-b-cand",
            "2",
            "--b-prop",
            "0.5",
            "--a-coh",
            "0.7",
            "--b-coh",
            "0.7",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output.read_text() == "saved result"
