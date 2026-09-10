"""Check standalone scripts with separate input and output trees."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest

from pipelines.bradley_terry.collect_metrics import output_jobs
from voting_metrics_main_code.replication import ROOT


def test_runner_resolves_relative_data_before_changing_child_directory(tmp_path: Path) -> None:
    script = ROOT / "scripts/replicate.py"
    code = (
        "import json, runpy, subprocess, sys; "
        "subprocess.run = lambda *args, **kw: print(json.dumps(args[0])); "
        "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(script),
            "ny",
            "--mode",
            "stats",
            "--data-dir",
            "inputs",
            "--output-dir",
            "output",
        ],
        cwd=tmp_path,
        env={**os.environ, "QF_DATA_DIR": "inputs", "QF_RESULTS_DIR": str(tmp_path / "output")},
        capture_output=True,
        text=True,
        check=True,
    )
    command = json.loads(result.stdout.splitlines()[-1])
    assert command[command.index("--data-dir") + 1] == str(tmp_path / "inputs")


def test_bt_paired_statistics_keep_the_selected_root(tmp_path: Path) -> None:
    tree = tmp_path / "sigma_IIA-run"
    output_jobs = runpy.run_path(str(ROOT / "pipelines/bradley_terry/collect_metrics.py"))[
        "output_jobs"
    ]
    folder = tmp_path / "02_06/b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)"
    for rule in ("borda", "stv", "plurality", "2-approval", "3-approval", "ranked-pairs", "random"):
        _, jobs = output_jobs(folder, 3, rule, "lex", output_root=ROOT)
        for _, _, _, path in jobs:
            destination = tree.joinpath(*path.parts[-5:])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("[0.2, 0.3]")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipelines/bradley_terry/plots/plot_um_iia_scatter.py"),
            "--bt-stats-dir",
            str(tree),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            "QF_BT_STATS_DIR": str(tree),
            "QF_RESULTS_DIR": str(tmp_path / "output"),
        },
        capture_output=True,
        check=True,
    )
    assert len(list((tmp_path / "output").rglob("*.png"))) == 14


def test_proportionality_keeps_profile_and_utility_roots(tmp_path: Path) -> None:
    from votekit import RankProfile

    generate = runpy.run_path(str(ROOT / "pipelines/bradley_terry/generate_profiles.py"))[
        "generate_and_save_profile"
    ]
    process = runpy.run_path(str(ROOT / "pipelines/bradley_terry/compute_proportionality.py"))[
        "process_profile"
    ]
    data = tmp_path / "preference_profiles/b_proportion_bad.csv/_COHESION_(bad)"
    generate(2, 2, 40, 0.5, 0.7, 0.7, 1, 1, 1, 1, 0, str(data / "preference_profiles"))
    profile = next((data / "preference_profiles").rglob("*.csv"))
    result = process(str(profile), RankProfile.from_csv(profile))
    assert len(result[str(profile)]) == 7


def test_standalone_defaults_ignore_old_environment_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QF_RESULTS_DIR", str(tmp_path / "old-override"))
    monkeypatch.setenv("QF_DATA_DIR", str(tmp_path / "old-data"))
    monkeypatch.setenv("QF_BT_STATS_DIR", str(tmp_path / "old-statistics"))
    monkeypatch.setattr(sys, "argv", ["replicate.py", "bt", "--mode", "figures", "--dry-run"])
    runner = runpy.run_path(str(ROOT / "scripts/replicate.py"))
    args = runner["parse_arguments"]()
    assert args.output_dir == ROOT
    assert args.data_dir == ROOT / "data"
    assert args.stats_dir == ROOT / "stats"
    assert args.bt_stats_dir == ROOT / "stats/bt_2_bloc_profile_stats"


@pytest.mark.parametrize("mode", ["all", "figures"])
@pytest.mark.parametrize("dataset", ["ny", "portland", "scottish", "bt"])
def test_runner_selects_statistics_for_its_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, dataset: str
) -> None:
    main = runpy.run_path(str(ROOT / "scripts/replicate.py"))["main"]
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["replicate.py", dataset, "--mode", mode, "--output-dir", "new-results"]
    )
    main()
    expected = tmp_path / "new-results/stats"
    assert calls
    for args, kwargs in calls:
        assert Path(args[0][1]).is_file()
        command = args[0]
        if "--stats-dir" in command:
            assert Path(command[command.index("--stats-dir") + 1]) == expected
        if "--bt-stats-dir" in command:
            assert (
                Path(command[command.index("--bt-stats-dir") + 1])
                == expected / "bt_2_bloc_profile_stats"
            )
        assert Path(command[command.index("--output-dir") + 1]) == tmp_path / "new-results"
        assert kwargs["env"]["PYTHONHASHSEED"] == "0"


def test_bootstrap_plot_imports_without_project_on_pythonpath(tmp_path: Path) -> None:
    path = ROOT / "pipelines/scottish/plots/plot_um_iia_bootstrap.py"
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["QF_RESULTS_DIR"] = str(tmp_path / "results")
    subprocess.run(
        [sys.executable, "-c", "import runpy, sys; runpy.run_path(sys.argv[1])", str(path)],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
    )


def test_bootstrap_plots_can_select_generated_intervals_separately(tmp_path: Path) -> None:
    intervals = tmp_path / "generated-intervals"
    intervals.mkdir()
    for suffix in ("", "_winner_set"):
        filename = (
            f"bootstrap_rectangles_sigma_IIA{suffix}_average"
            f"_vs_sigma_UM{suffix}_worst_case_asin.csv"
        )
        (intervals / filename).write_text(
            "rule,tiebreak,candidate_size,um_L,um_U,iia_L,iia_U\nborda,lex,,0.6,0.8,0.5,0.7\n"
        )
    module = runpy.run_path(str(ROOT / "pipelines/scottish/plots/plot_um_iia_bootstrap.py"))
    pairs = module["get_limited_metric_key_pairs"]()
    rows = module["load_rectangle_lookup"](intervals, pairs, "lex")
    assert len(rows) == 2
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipelines/scottish/plots/plot_bootstrap_rectangles.py"),
            "--bootstrap-dir",
            str(intervals),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(list((tmp_path / "output/plots/scottish/bonferroni_rectangles").glob("*.png"))) == 2


def test_bootstrap_candidate_count_plot(tmp_path: Path) -> None:
    module = runpy.run_path(str(ROOT / "pipelines/scottish/plots/plot_um_iia_bootstrap.py"))
    um_key, iia_key = module["get_limited_metric_key_pairs"]()[0]
    module["run_limited_scatter_plots_by_candidate_count_with_bootstrap"](
        outputs_by_election_type={"borda": {"3": {um_key: [0.6, 0.8], iia_key: [0.5, 0.7]}}},
        ordered_rules=["borda"],
        output_dir=tmp_path,
        metric_pairs=[(um_key, iia_key)],
        variant_um="worst_case",
        variant_iia="average",
        tiebreak="lex",
        rectangle_lookup={},
    )
    assert len(list(tmp_path.rglob("*.png"))) == 1


def test_histograms_create_fresh_output_directories(tmp_path: Path) -> None:
    module = runpy.run_path(str(ROOT / "pipelines/cross_dataset/plot_m_statistic_histograms.py"))
    bt = module["make_bt_M_histograms"]
    scottish = module["make_scottish_M_histogram"]
    folder = tmp_path / "02_06/b_proportion_0.7__ALPHA_(1.00,0.50,1.00,0.50)__COHESION_(0.70,0.90)"
    _, jobs = output_jobs(folder, 2, "borda", "lex", output_root=tmp_path)
    for _, _, _, source in jobs:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("[0.2, 0.3]")

    bt(
        "borda",
        [0.7],
        output_root=tmp_path,
        bt_stats_root=tmp_path / "stats/bt_2_bloc_profile_stats",
        n_seats=2,
    )
    scottish_folder = tmp_path / "stats/scottish_stats/sigma_UM_worst_case_asin/borda"
    scottish_folder.mkdir(parents=True)
    source = scottish_folder / "borda_lex_output.json"
    source.write_text(json.dumps({"3": {"first.csv": 0.2, "second.csv": 0.3}}))
    scottish("borda", output_root=tmp_path, stats_root=tmp_path / "stats")
    assert len(list((tmp_path / "plots/bt_plots/M_histograms").glob("*.png"))) == 3
    assert len(list((tmp_path / "plots/scottish/M_histograms").glob("*.png"))) == 1


def test_waterfall_uses_selected_inputs_without_stale_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main = runpy.run_path(
        str(ROOT / "pipelines/bradley_terry/plots/plot_proportionality_waterfall.py")
    )["main"]
    settings = "02_06/b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)"
    source = tmp_path / "stats/bt_proportionality"
    source.mkdir(parents=True)
    monkeypatch.setitem(main.__globals__, "AllowedRule", ("borda",))
    monkeypatch.setitem(
        main.__globals__,
        "product",
        lambda *args: [((2, 6), 0.5, (0.7, 0.7), (1, 1, 1, 1))],
    )
    points = []

    def save_plot(path: str | Path, **kwargs: object) -> None:
        assert Path(path).parent.is_dir()
        points.append(tuple(np.asarray(plt.gca().lines[0].get_ydata())))

    monkeypatch.setattr(plt, "savefig", save_plot)
    for observed in (0.2, 0.4):
        data = {
            f"/alternate-inputs/preference_profiles/{settings}/profile_{index}.csv": {
                "borda": {"expected_proportion": 0.5, "observed_proportion": observed + delta}
            }
            for index, delta in enumerate((0, 0.2))
        }
        (source / "results.json").write_text(json.dumps(data))
        main(stats_root=tmp_path / "stats", output_root=tmp_path)
        plt.close("all")
    assert points[0] == pytest.approx((0.3,))
    assert points[1] == pytest.approx((0.5,))


def test_waterfall_reports_missing_input_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    main = runpy.run_path(
        str(ROOT / "pipelines/bradley_terry/plots/plot_proportionality_waterfall.py")
    )["main"]
    with pytest.raises(FileNotFoundError, match="bt_proportionality"):
        main(stats_root=tmp_path, output_root=tmp_path)


@pytest.mark.parametrize("dataset", ["ny", "portland", "scottish", "bt"])
def test_shell_runners_preserve_the_calling_directory(tmp_path: Path, dataset: str) -> None:
    executable = tmp_path / "uv"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:]}))\n"
    )
    executable.chmod(0o755)
    result = subprocess.run(
        [str(ROOT / f"scripts/run_{dataset}_pipeline.sh"), "--output-dir", "new-results"],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]},
        check=True,
        capture_output=True,
        text=True,
    )
    invocation = json.loads(result.stdout)
    assert invocation["cwd"] == str(tmp_path)
    assert invocation["args"][:6] == [
        "run",
        "--project",
        str(ROOT),
        "--locked",
        "python",
        str(ROOT / "scripts/replicate.py"),
    ]
    assert invocation["args"][-2:] == ["--output-dir", "new-results"]


def test_dry_run_prints_relative_inputs_without_writing(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/replicate.py"),
            "portland",
            "--dry-run",
            "--data-dir",
            "inputs",
            "--output-dir",
            "run",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "plot_boost_matrix.py" in result.stdout
    assert f"--data-dir {tmp_path / 'inputs'}" in result.stdout
    assert f"--stats-dir {tmp_path / 'run/stats'}" in result.stdout
    assert not (tmp_path / "run").exists()


def test_standalone_plot_selects_statistics_from_its_run_root(tmp_path: Path) -> None:
    source = tmp_path / "run/stats/bt_2_bloc_profile_stats"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "pipelines/bradley_terry/plots/plot_um_iia_scatter.py"),
            "--output-dir",
            "run",
            "--n-seats",
            "2",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert f"{source}/2_seats" in result.stderr
    assert "No saved BT results match" in result.stderr
    assert not list((tmp_path / "run").rglob("*.png"))
