"""Check that alpha pooling preserves raw observations and separates experiment selections."""

import json
from itertools import product
from pathlib import Path

import pytest

from pipelines.bradley_terry import pool_alpha_metrics as pooling
from pipelines.bradley_terry.collect_metrics import output_jobs
from pipelines.bradley_terry.plots.plot_alpha_boxplots import load_alpha_samples


def test_pooling_keeps_alpha_rule_and_total_size_and_preserves_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alphas = ((1, 1, 1, 1), (1, 0.5, 1, 0.5))
    splits = ((2, 6), (4, 4), (2, 8))
    monkeypatch.setattr(pooling, "BT_ALPHA_COMBINATIONS", alphas)
    monkeypatch.setattr(pooling, "BT_CANDIDATE_COMBINATIONS", splits)
    monkeypatch.setattr(pooling, "BT_BLOC_PROPORTIONS", (0.5, 0.7))
    monkeypatch.setattr(pooling, "BT_COHESION_COMBINATIONS", ((0.7, 0.9),))
    monkeypatch.setattr(pooling, "COMPARISON_RULE_ORDER", ("borda", "stv"))
    expected: dict[tuple[tuple[float, ...], int, str], list[float]] = {}
    originals: dict[Path, bytes] = {}

    for alpha, split, proportion, rule in product(alphas, splits, (0.5, 0.7), ("borda", "stv")):
        alpha_token = ",".join(f"{value:.2f}" for value in alpha)
        folder = (
            tmp_path
            / f"{split[0]:02d}_{split[1]:02d}"
            / (f"b_proportion_{proportion}__ALPHA_({alpha_token})__COHESION_(0.70,0.90)")
        )
        _, jobs = output_jobs(folder, 3, rule, "lex", output_root=tmp_path)
        path = next(path for _, _, _, path in jobs if path.name.startswith("METRIC_sigma_IIA__"))
        path.parent.mkdir(parents=True, exist_ok=True)
        scores = [proportion, split[0] / 10]
        path.write_text(json.dumps(scores))
        originals[path] = path.read_bytes()
        expected.setdefault((alpha, sum(split), rule), []).extend(scores)
        path.with_name(path.name.replace("TIEBREAK_lex", "TIEBREAK_random")).write_text("invalid")
        path.with_name(path.name.replace("VARIANT_average", "VARIANT_worst_case")).write_text(
            "invalid"
        )

    source_root = tmp_path / "stats/bt_2_bloc_profile_stats"
    groups = pooling.pool_metric_scores(source_root, "sigma_IIA", "average", "None", 3, "lex")
    assert len(groups) == 8
    for group in groups:
        key = (tuple(group["alpha"]), group["n_cands"], group["rule"])
        assert sorted(group["scores"]) == sorted(expected[key])
        source_paths = [source_root / relative for relative in group["source_files"]]
        assert group["scores"] == [
            score for path in source_paths for score in json.loads(originals[path])
        ]

    pooled_root = tmp_path / "stats/bt_alpha_grouped"
    destination = pooling.grouped_scores_path(pooled_root, "sigma_IIA", "average", "None", 3, "lex")
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(groups))
    loaded = load_alpha_samples(
        "sigma_IIA", alphas[1], ("borda", "stv"), (8, 10), pooled_root, 3, "average", "lex", "None"
    )
    assert sorted(loaded["borda"][8]) == sorted(expected[(alphas[1], 8, "borda")])
    assert all(path.read_bytes() == contents for path, contents in originals.items())

    next(iter(originals)).unlink()
    with pytest.raises(ValueError, match="Incomplete or duplicate BT grid"):
        pooling.pool_metric_scores(source_root, "sigma_IIA", "average", "None", 3, "lex")


@pytest.mark.parametrize("contents", ["[]", "[true]", "[NaN]", "[0.1, 0.2]"])
def test_pooling_rejects_invalid_or_unequal_profile_arrays(tmp_path: Path, contents: str) -> None:
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text("[0.5]")
    second.write_text(contents)
    with pytest.raises(ValueError):
        pooling.load_complete_samples([str(first), str(second)])


def test_pooling_skips_existing_results_without_loading_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selections = (
        ("sigma_UM", "asin"),
        ("sigma_UM", "odds"),
        ("sigma_UM_winner_set", "asin"),
        ("sigma_UM_winner_set", "odds"),
        ("sigma_IIA", "None"),
        ("sigma_IIA_winner_set", "None"),
    )
    for (metric, interpolation), variant in product(selections, ("average", "worst_case")):
        path = pooling.grouped_scores_path(
            tmp_path / "stats/bt_alpha_grouped", metric, variant, interpolation, 3, "lex"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("saved result")

    monkeypatch.setattr(
        pooling, "pool_metric_scores", lambda *args: pytest.fail("Reloaded sources")
    )
    pooling.main(bt_stats_root=tmp_path / "missing", output_root=tmp_path)
    assert all(path.read_text() == "saved result" for path in tmp_path.rglob("*.json"))
