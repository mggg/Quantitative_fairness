"""Check standalone scripts with separate input and output trees."""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from voting_metrics_main_code.replication import ROOT


def test_runner_resolves_relative_data_before_changing_child_directory(tmp_path):
    script = ROOT / "scripts/replicate.py"
    code = (
        "import json, runpy, subprocess, sys; "
        "subprocess.run = lambda *args, **kw: print(json.dumps(kw['env']['QF_DATA_DIR'])); "
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
            "--output-dir",
            "output",
        ],
        cwd=tmp_path,
        env={**os.environ, "QF_DATA_DIR": "inputs", "QF_RESULTS_DIR": str(tmp_path / "output")},
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == str(tmp_path / "inputs")


def test_bt_paired_statistics_keep_the_selected_root(tmp_path):
    tree = tmp_path / "sigma_IIA-run"
    output_jobs = runpy.run_path(ROOT / "pipelines/bradley_terry/collect_metrics.py")["output_jobs"]
    folder = tmp_path / "02_06/b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)"
    for rule in ("borda", "stv", "plurality", "2-approval", "3-approval", "ranked-pairs", "random"):
        _, jobs = output_jobs(folder, 3, rule, "lex")
        for _, _, _, path in jobs:
            destination = tree.joinpath(*path.parts[-5:])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("[0.2, 0.3]")
    subprocess.run(
        [sys.executable, str(ROOT / "pipelines/bradley_terry/plots/plot_um_iia_scatter.py")],
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


def test_proportionality_keeps_profile_and_utility_roots(tmp_path):
    from votekit import RankProfile

    generate = runpy.run_path(ROOT / "pipelines/bradley_terry/generate_profiles.py")[
        "generate_and_save_profile"
    ]
    process = runpy.run_path(ROOT / "pipelines/bradley_terry/compute_proportionality.py")[
        "process_profile"
    ]
    data = tmp_path / "preference_profiles/b_proportion_bad.csv/_COHESION_(bad)"
    generate(2, 2, 40, 0.5, 0.7, 0.7, 1, 1, 1, 1, 0, str(data / "preference_profiles"))
    profile = next((data / "preference_profiles").rglob("*.csv"))
    result = process(str(profile), RankProfile.from_csv(profile))
    assert len(result[str(profile)]) == 7


def test_standalone_defaults_and_explicit_inputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("QF_DATA_DIR", "QF_STATS_DIR", "QF_BT_STATS_DIR", "QF_BOOTSTRAP_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("QF_RESULTS_DIR", str(tmp_path / "new-results"))
    paths = runpy.run_path(ROOT / "voting_metrics_main_code/replication.py")
    assert paths["STATS_INPUT"] == ROOT / "stats"
    assert paths["BT_STATS_INPUT"] == ROOT / "stats/bt_2_bloc_profile_stats"
    assert paths["STATS_OUTPUT"] == tmp_path / "new-results/stats"

    monkeypatch.setenv("QF_STATS_DIR", "selected-statistics")
    monkeypatch.setenv("QF_BT_STATS_DIR", "selected-bt-tree")
    monkeypatch.setenv("QF_BOOTSTRAP_DIR", "new-results/stats/scottish_stats/bootstrap")
    paths = runpy.run_path(ROOT / "voting_metrics_main_code/replication.py")
    assert paths["STATS_INPUT"] == tmp_path / "selected-statistics"
    assert paths["BT_STATS_INPUT"] == tmp_path / "selected-bt-tree"
    assert paths["SCOTTISH_BOOTSTRAP_INPUT"] == (
        tmp_path / "new-results/stats/scottish_stats/bootstrap"
    )


@pytest.mark.parametrize("mode", ["all", "figures"])
@pytest.mark.parametrize("dataset", ["ny", "portland", "scottish", "bt"])
def test_runner_selects_statistics_for_its_mode(tmp_path, monkeypatch, mode, dataset):
    main = runpy.run_path(ROOT / "scripts/replicate.py")["main"]
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["replicate.py", dataset, "--mode", mode, "--output-dir", "new-results"]
    )
    main()
    expected = ROOT / "stats" if mode == "figures" else tmp_path / "new-results/stats"
    assert calls
    for args, kwargs in calls:
        assert Path(args[0][1]).is_file()
        assert Path(kwargs["env"]["QF_STATS_DIR"]) == expected
        assert Path(kwargs["env"]["QF_RESULTS_DIR"]) == tmp_path / "new-results"


def test_bootstrap_plot_imports_without_project_on_pythonpath(tmp_path):
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


def test_bootstrap_plots_can_select_generated_intervals_separately(tmp_path):
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
    env = {
        **os.environ,
        "QF_STATS_DIR": str(tmp_path / "primary-statistics"),
        "QF_BOOTSTRAP_DIR": str(intervals),
        "QF_RESULTS_DIR": str(tmp_path / "output"),
    }
    for name in ("plot_um_iia_bootstrap", "plot_bootstrap_rectangles"):
        command = [sys.executable]
        if name == "plot_um_iia_bootstrap":
            command += [
                "-c",
                "import runpy, sys; m = runpy.run_path(sys.argv[1]); "
                "pairs = m['get_limited_metric_key_pairs'](); "
                "rows = m['load_rectangle_lookup'](m['SCOTTISH_BOOTSTRAP_INPUT'], pairs, 'lex'); "
                "assert len(rows) == 2",
            ]
        result = subprocess.run(
            [*command, str(ROOT / f"pipelines/scottish/plots/{name}.py")],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Missing rectangle file" not in result.stdout
    assert len(list((tmp_path / "output/plots/scottish/bonferroni_rectangles").glob("*.png"))) == 2


def test_bootstrap_candidate_count_plot(tmp_path):
    module = runpy.run_path(ROOT / "pipelines/scottish/plots/plot_um_iia_bootstrap.py")
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


def test_histograms_create_fresh_output_directories(tmp_path, monkeypatch):
    module = runpy.run_path(ROOT / "pipelines/cross_dataset/plot_m_statistic_histograms.py")
    bt = module["make_bt_M_histograms"]
    scottish = module["make_scottish_M_histogram"]
    source = tmp_path / "source.json"
    source.write_text(json.dumps([0.2, 0.3]))
    monkeypatch.setitem(bt.__globals__, "glob", lambda *args, **kwargs: [str(source)])
    monkeypatch.setitem(bt.__globals__, "bt_plots_dir", tmp_path / "bt")
    monkeypatch.setitem(scottish.__globals__, "scottish_plots_dir", tmp_path / "scottish")
    bt("borda", [0.7])
    source.write_text(json.dumps({"3": {"first.csv": 0.2, "second.csv": 0.3}}))
    scottish("borda")
    assert len(list((tmp_path / "bt").glob("*.png"))) == 3
    assert len(list((tmp_path / "scottish").glob("*.png"))) == 1


def test_waterfall_uses_selected_inputs_without_stale_cache(tmp_path, monkeypatch):
    main = runpy.run_path(ROOT / "pipelines/bradley_terry/plots/plot_proportionality_waterfall.py")[
        "main"
    ]
    settings = "02_06/b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)"
    source = tmp_path / "stats/bt_proportionality"
    source.mkdir(parents=True)
    monkeypatch.setitem(main.__globals__, "STATS_INPUT", tmp_path / "stats")
    monkeypatch.setitem(main.__globals__, "PLOTS_DIR", tmp_path / "plots")
    monkeypatch.setitem(main.__globals__, "AllowedRule", ("borda",))
    monkeypatch.setitem(
        main.__globals__,
        "product",
        lambda *args: [((2, 6), 0.5, (0.7, 0.7), (1, 1, 1, 1), 0)],
    )
    points = []

    def save_plot(path, **kwargs):
        assert Path(path).parent.is_dir()
        points.append(tuple(plt.gca().lines[0].get_ydata()))

    monkeypatch.setattr(plt, "savefig", save_plot)
    for observed in (0.2, 0.4):
        data = {
            f"/alternate-inputs/preference_profiles/{settings}/profile_{index}.csv": {
                "borda": {"expected_proportion": 0.5, "observed_proportion": observed + delta}
            }
            for index, delta in enumerate((0, 0.2))
        }
        (source / "results.json").write_text(json.dumps(data))
        main()
        plt.close("all")
    assert points[0] == pytest.approx((0.3,))
    assert points[1] == pytest.approx((0.5,))


def test_waterfall_reports_missing_input_directory(tmp_path, monkeypatch):
    main = runpy.run_path(ROOT / "pipelines/bradley_terry/plots/plot_proportionality_waterfall.py")[
        "main"
    ]
    monkeypatch.setitem(main.__globals__, "STATS_INPUT", tmp_path)
    with pytest.raises(FileNotFoundError, match="bt_proportionality"):
        main()


@pytest.mark.parametrize("dataset", ["ny", "portland", "scottish", "bt"])
def test_shell_runners_preserve_the_calling_directory(tmp_path, dataset):
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
