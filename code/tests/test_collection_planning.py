"""Check metric selection and the boundary between planning and protected publication."""

from pathlib import Path

import pytest

from pipelines.bradley_terry._metrics import IIAMetric, UMMetric, parse_metric_spec
from pipelines.bradley_terry.collect_metrics import (
    OutputProgress,
    build_output_jobs,
    execute_collection,
    plan_collection,
    publish_completed_scores,
)
from pipelines.bradley_terry.collect_single_folder_metrics import build_output_path


def test_planning_preserves_paths_and_defers_all_writes(tmp_path: Path) -> None:
    folder = tmp_path / "02_02/b_proportion_0.5__ALPHA_(1,1,1,1)__COHESION_(0.7,0.9)"
    folder.mkdir(parents=True)
    output_root = tmp_path / "run"
    _, jobs = build_output_jobs(folder, 2, "borda", "lex", output_root=output_root)
    for job in jobs:
        spec = job.spec
        interpolation = spec.interpolation if isinstance(spec, UMMetric) else "None"
        _, single_path = build_output_path(
            folder, 2, spec.name, spec.variant, interpolation, "borda", "lex", output_root
        )
        assert single_path == job.path

    plan = plan_collection([folder], 2, "borda", "lex", 1, output_root=output_root)
    assert not output_root.exists()
    assert not plan.tasks
    assert len(plan.outputs) == 4
    assert execute_collection(plan, n_jobs=1, seed=0) == 4
    assert all(job.path.read_text() == "[]" for job in jobs)

    resumed = plan_collection([folder], 2, "borda", "lex", 1, output_root=output_root)
    assert resumed.skipped == 4
    assert not resumed.outputs


def test_publication_requires_every_score_and_batch(tmp_path: Path) -> None:
    destination = tmp_path / "scores.json"
    output = OutputProgress(destination, [0.25, None], 0, "test")
    with pytest.raises(ValueError, match="Incomplete"):
        publish_completed_scores(output)
    assert not destination.exists()

    output.scores[1] = 0.75
    output.remaining_batches = 1
    with pytest.raises(ValueError, match="Incomplete"):
        publish_completed_scores(output)
    assert not destination.exists()

    output.remaining_batches = 0
    publish_completed_scores(output)
    assert destination.read_text() == "[0.25, 0.75]"


def test_metric_settings_distinguish_um_interpolation_from_iia() -> None:
    assert parse_metric_spec("sigma_UM", "average", "linear") == UMMetric(
        "sigma_UM", "average", "linear"
    )
    assert parse_metric_spec("sigma_IIA", "average", "None") == IIAMetric("sigma_IIA", "average")
    with pytest.raises(ValueError, match="interpolation"):
        parse_metric_spec("sigma_UM", "average", "None")
    with pytest.raises(ValueError, match="variant"):
        parse_metric_spec("sigma_IIA", "unknown", "None")
