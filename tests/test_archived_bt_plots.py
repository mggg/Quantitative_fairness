"""Check that archived BT workflows run independently of the main BT pipeline copy."""

import os
import subprocess
import sys
from pathlib import Path

from voting_metrics_main_code.replication import ROOT


def test_archived_commands_use_archive_helpers_and_defaults_from_another_directory(
    tmp_path: Path,
) -> None:
    code = """
import ast
import runpy
import sys
from pathlib import Path

class BlockMainPipelines:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'pipelines' or fullname.startswith('pipelines.'):
            raise ImportError(f'Archived workflow imported the main pipeline: {fullname}')

sys.meta_path.insert(0, BlockMainPipelines())
root = Path(sys.argv[1])
folder = root / 'archive/pipelines/bradley_terry'
for path in sorted(folder.rglob('*.py')):
    module = runpy.run_path(str(path))
    if 'main' not in module:
        continue

    main = module['main']
    callback = getattr(main, 'callback', main)
    expected_output = root if path.name == 'pool_alpha_metrics.py' else root / 'archive'
    assert callback.__kwdefaults__['output_root'] == expected_output, path

    sys.argv = [str(path), '--help']
    try:
        runpy.run_path(str(path), run_name='__main__')
    except SystemExit as error:
        assert error.code == 0, (path, error.code)
    else:
        raise AssertionError(f'{path} did not display help')

helpers = sys.modules['archive.pipelines.bradley_terry.plots._data']
assert Path(helpers.__file__).is_relative_to(folder)
assert 'archive.pipelines.bradley_terry.pool_alpha_metrics' in sys.modules
"""
    subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(ROOT)],
        cwd=tmp_path,
        env={**os.environ, "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(tmp_path / "matplotlib")},
        check=True,
        capture_output=True,
        text=True,
    )


def test_archived_alpha_plot_reads_saved_scores_and_writes_to_selected_output(
    tmp_path: Path,
) -> None:
    from archive.pipelines.bradley_terry.plots.plot_alpha_sweep import plot_metric

    source = tmp_path / "inputs/3_seats/sigma_IIA/08/borda"
    source.mkdir(parents=True)
    from voting_metrics_main_code.constants import BT_ALPHA_COMBINATIONS

    for alpha in BT_ALPHA_COMBINATIONS:
        token = ",".join(f"{value:.2f}" for value in alpha)
        path = source / (
            "METRIC_sigma_IIA__VARIANT_average__INTERP_None__NCANDS_(02_06)__SEATS_3"
            f"__BPROP_0.5__ALPHA_({token})__COHESION_(0.70,0.90)__TYPE_borda__TIEBREAK_lex.json"
        )
        path.write_text("[0.2, 0.6]")

    plot_metric(
        "sigma_IIA",
        "average",
        "None",
        bt_stats_root=tmp_path / "inputs",
        output_root=tmp_path / "output",
    )
    output = tmp_path / (
        "output/plots/bt_plots/alpha_sweep_plots/"
        "sigma_IIA__average__mean_vs_std_colored_by_alpha.png"
    )
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert all(path.read_text() == "[0.2, 0.6]" for path in source.iterdir())
