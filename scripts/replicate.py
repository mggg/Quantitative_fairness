"""Run maintained analyses, preserving computed results and refreshing derived outputs."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voting_metrics_main_code.constants import RULE_ORDER  # noqa: E402
from voting_metrics_main_code.replication import DATA_DIR  # noqa: E402


def parse_arguments() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ny", "portland", "scottish", "bt"))
    parser.add_argument("--mode", choices=("stats", "figures", "all"), default="all")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/generated")
    parser.add_argument("--stats-dir", type=Path, help="Existing statistics for figures mode")
    parser.add_argument("--bt-stats-dir", type=Path, help="Exact BT result tree for figures mode")
    parser.add_argument("--settings-file", type=Path, default=ROOT / "config/bt_profiles.txt")
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--diagnostics", action="store_true", help="Also run Portland clustering")
    args = parser.parse_args()
    if args.n_jobs < 1:
        parser.error("--n-jobs must be positive")
    if args.mode != "figures" and (args.stats_dir or args.bt_stats_dir):
        parser.error("--stats-dir and --bt-stats-dir are only used in figures mode")
    if args.diagnostics and args.dataset != "portland":
        parser.error("--diagnostics is only available for Portland")
    return parser, args


def main() -> None:
    parser, args = parse_arguments()
    output = args.output_dir.resolve()
    stats = (
        args.stats_dir or (ROOT / "stats" if args.mode == "figures" else output / "stats")
    ).resolve()
    bt_stats = (args.bt_stats_dir or stats / "bt_2_bloc_profile_stats").resolve()
    settings = args.settings_file.resolve()
    if args.dataset == "bt" and args.mode != "figures" and not settings.is_file():
        parser.error(f"Settings file does not exist: {settings}")
    source = bt_stats if args.dataset == "bt" else stats / f"{args.dataset}_stats"
    if args.mode == "figures" and not any(source.rglob("*.json")):
        parser.error(f"No statistics found under {source}")

    env = os.environ.copy()
    env.update(
        {
            "QF_DATA_DIR": str(DATA_DIR),
            "QF_RESULTS_DIR": str(output),
            "QF_STATS_DIR": str(stats),
            "QF_BT_STATS_DIR": str(bt_stats),
            "QF_SEED": str(args.seed),
            "QF_N_JOBS": str(args.n_jobs),
            "PYTHONHASHSEED": "0",
            "MPLBACKEND": "Agg",
            "PYTHONPATH": str(ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset": args.dataset,
        "seed": args.seed,
        "python": sys.version,
        "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
        "settings_sha256": hashlib.sha256(settings.read_bytes()).hexdigest()
        if args.dataset == "bt" and args.mode != "figures"
        else None,
    }
    if args.mode != "figures":
        record = output / f"{args.dataset}-run.json"
        if record.exists() and json.loads(record.read_text()) != manifest:
            parser.error(
                "Run settings differ from this output directory; choose a new --output-dir"
            )
        record.write_text(json.dumps(manifest, indent=2) + "\n")

    def run(relative_path: str, *options: str | int | Path) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / relative_path), *map(str, options)],
            cwd=ROOT,
            env=env,
            check=True,
        )

    if args.mode != "figures":
        if args.dataset == "bt":
            for rule in RULE_ORDER:
                run(
                    "pipelines/bradley_terry/collect_metrics.py",
                    "--settings-file",
                    settings,
                    "--election-type",
                    rule,
                    "--n-jobs",
                    args.n_jobs,
                )
        else:
            folder = "new_york" if args.dataset == "ny" else args.dataset
            run(f"pipelines/{folder}/collect_metrics.py")
    if args.mode != "stats":
        if args.dataset == "bt":
            for name in (
                "plot_um_iia_scatter",
                "plot_candidate_count_boxplots",
                "plot_bloc_proportion_boxplots",
            ):
                run(f"pipelines/bradley_terry/plots/{name}.py")
        elif args.dataset == "scottish":
            run("pipelines/scottish/plots/plot_um_iia_scatter.py")
            run("pipelines/scottish/export_metric_tables.py")
        else:
            run("scripts/export_tables.py", args.dataset)
    if args.diagnostics:
        run("pipelines/portland/clustering/run_short_bursts.py")
        run("pipelines/portland/clustering/run_brute_force.py")


if __name__ == "__main__":
    main()
