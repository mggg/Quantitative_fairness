"""Check explicit BT experiment selection and pairing against the collector's filenames."""

import json
from pathlib import Path

import pytest

from pipelines.bradley_terry.collect_metrics import output_jobs
from pipelines.bradley_terry.plots._data import find_metric_files, paired_metric_file
from pipelines.bradley_terry.plots.plot_um_iia_scatter import load_paired_metrics


def test_selection_and_pairing_keep_settings_and_input_root(tmp_path: Path) -> None:
    run = tmp_path / "sigma_IIA-run"
    folder = tmp_path / "02_06/b_proportion_0.5__ALPHA_(1.00,0.50,1.00,0.50)__COHESION_(0.70,0.90)"
    for seats in (2, 3):
        _, jobs = output_jobs(folder, seats, "borda", "lex", output_root=run)
        for _, _, _, path in jobs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[0.2, 0.3]")
    root = run / "stats/bt_2_bloc_profile_stats"
    files = find_metric_files(
        root,
        "sigma_IIA",
        "average",
        "None",
        n_seats=2,
        rule="borda",
        candidate_counts=(2, 6),
        bloc_proportion=0.5,
        alpha=(1, 0.5, 1, 0.5),
        cohesion=(0.7, 0.9),
    )
    assert len(files) == 1
    assert Path(files[0]).relative_to(root).parts[0] == "2_seats"
    companion = paired_metric_file(Path(files[0]), "sigma_UM", "worst_case", "asin")
    assert companion.is_relative_to(root)
    assert companion.is_file()
    assert load_paired_metrics(
        "sigma_IIA", "borda", "average", "worst_case", "lex", bt_stats_root=root, n_seats=2
    ) == ([0.2, 0.3], [0.2, 0.3])

    companion.write_text("[0.2]")
    with pytest.raises(ValueError, match="Paired score counts differ"):
        load_paired_metrics(
            "sigma_IIA", "borda", "average", "worst_case", "lex", bt_stats_root=root, n_seats=2
        )


def test_missing_experiment_reports_its_selection(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="__SEATS_2.*__TYPE_borda"):
        find_metric_files(tmp_path, "sigma_IIA", "average", "None", n_seats=2, rule="borda")


def test_selection_treats_brackets_in_the_input_root_literally(tmp_path: Path) -> None:
    folder = tmp_path / "02_06/b_proportion_0.5__ALPHA_(1.00,0.50,1.00,0.50)__COHESION_(0.70,0.90)"
    for name, score in (("run[1]", 0.1), ("run1", 0.9)):
        _, jobs = output_jobs(folder, 3, "borda", "lex", output_root=tmp_path / name)
        for _, _, _, path in jobs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps([score]))

    selected_root = tmp_path / "run[1]/stats/bt_2_bloc_profile_stats"
    paths = find_metric_files(selected_root, "sigma_IIA", "average", "None", rule="borda")
    assert len(paths) == 1
    assert Path(paths[0]).is_relative_to(selected_root)
    assert json.loads(Path(paths[0]).read_text()) == [0.1]
