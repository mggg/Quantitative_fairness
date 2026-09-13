"""Check paired bootstrap alignment, numerical bounds, and exported row conventions."""

import json

import numpy as np
import pytest

from pipelines.scottish.compute_bootstrap_intervals import (
    bootstrap_confidence_rectangle,
    build_rectangle_rows_for_file_pair,
)


def test_rectangles_align_election_ids_and_preserve_exported_bounds() -> None:
    iia = {"8": {"c": 0.8, "a": 0.2}, "4": {"b": 0.5, "a": 0.1}}
    um = {"4": {"a": 0.9, "b": 0.6}, "8": {"a": 0.7, "c": 0.3, "extra": 1.0}}
    rectangle = bootstrap_confidence_rectangle(
        iia, um, n_resamples=100, alpha=0.2, seed=17, return_samples=True
    )

    assert rectangle.samples is not None
    np.testing.assert_array_equal(
        rectangle.samples.paired, [[0.1, 0.9], [0.5, 0.6], [0.2, 0.7], [0.8, 0.3]]
    )
    assert rectangle.n_pairs == 4
    assert rectangle.overlap_counts == {"4": 2, "8": 2}
    assert (
        rectangle.iia_lower,
        rectangle.iia_upper,
        rectangle.um_lower,
        rectangle.um_upper,
    ) == pytest.approx((0.15, 0.575, 0.475, 0.8))

    rows = build_rectangle_rows_for_file_pair("IIA", "UM", "borda", "lex", iia, um, 100, 0.2, 17)
    assert np.isnan(rows[0]["candidate_size"])
    assert [row["candidate_size"] for row in rows[1:]] == [4, 8]
    assert rows[0]["iia_L"] == rectangle.iia_lower
    assert rows[0]["um_U"] == rectangle.um_upper
    assert json.loads(rows[0]["sizes_used"]) == ["4", "8"]
    assert json.loads(rows[0]["overlap_counts_by_size"]) == {"4": 2, "8": 2}
    assert bootstrap_confidence_rectangle(iia, um, n_resamples=10).samples is None


@pytest.mark.parametrize("n_resamples,alpha", [(1, 0.05), (10, 0), (10, 1)])
def test_rectangles_reject_invalid_resampling_parameters(n_resamples: int, alpha: float) -> None:
    with pytest.raises(ValueError):
        bootstrap_confidence_rectangle(
            {"4": {"a": 0.5}}, {"4": {"a": 0.5}}, n_resamples=n_resamples, alpha=alpha
        )
