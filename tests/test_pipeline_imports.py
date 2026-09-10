"""Check that pipeline imports do not run analyses or create output files."""

import os
import subprocess
import sys
from pathlib import Path

from pipelines.bradley_terry.plots._data import load_metric_samples, load_metric_summaries
from voting_metrics_main_code.replication import ROOT


def test_pipeline_imports_do_not_require_data_or_render_figures(tmp_path: Path) -> None:
    output = tmp_path / "output"
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update(
        QF_DATA_DIR=str(tmp_path / "missing-data"),
        QF_STATS_DIR=str(tmp_path / "missing-statistics"),
        QF_BT_STATS_DIR=str(tmp_path / "missing-bt-statistics"),
        QF_BOOTSTRAP_DIR=str(tmp_path / "missing-intervals"),
        QF_RESULTS_DIR=str(output),
        MPLBACKEND="Agg",
    )
    code = """
import runpy
import sys
from pathlib import Path
import matplotlib.pyplot as plt

for path in sorted(Path(sys.argv[1]).rglob('*.py')):
    runpy.run_path(str(path))
    assert not plt.get_fignums(), path
"""
    subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "pipelines")],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert not output.exists()


def test_metric_loaders_preserve_file_and_observation_order(tmp_path: Path) -> None:
    first = tmp_path / "z.json"
    second = tmp_path / "a.json"
    first.write_text("[3, 1]")
    second.write_text("[8, 4]")
    paths = [str(first), str(second)]

    assert load_metric_samples(paths) == [3, 1, 8, 4]
    assert load_metric_summaries(paths) == [[2.0, 1.0], [6.0, 2.0]]
    assert load_metric_summaries(paths, "var") == [[2.0, 1.0], [6.0, 4.0]]
