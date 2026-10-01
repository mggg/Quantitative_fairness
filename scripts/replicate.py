"""Run the primary dataset recipes; use --dry-run to inspect their commands."""

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voting_metrics_main_code.constants import RULE_ORDER  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Resolve the recipe's inputs and output root relative to the calling directory.

    Returns:
        argparse.Namespace: Validated recipe options with input and output paths resolved.

    Raises:
        SystemExit: Arguments are invalid or incompatible with the selected dataset or mode.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ny", "portland", "scottish", "bt"))
    parser.add_argument(
        "--mode",
        choices=("stats", "figures", "all"),
        default="all",
        help="Stages of the primary recipe, not every exploratory analysis",
    )
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT,
        help="Run root containing stats, plots, and tables (default: repository)",
    )
    parser.add_argument("--stats-dir", type=Path, help="Statistics parent for figures mode")
    parser.add_argument("--bt-stats-dir", type=Path, help="Exact BT tree for figures mode")
    parser.add_argument("--settings-file", type=Path, default=ROOT / "config/bt_profiles.txt")
    parser.add_argument(
        "--n-seats", type=int, default=3, help="Seats for the two-bloc BT experiment"
    )
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--diagnostics", action="store_true", help="Also run Portland clustering")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without running or writing"
    )
    args = parser.parse_args()

    if min(args.n_jobs, args.n_seats) < 1:
        parser.error("--n-jobs and --n-seats must be positive")
    if args.mode != "figures" and (args.stats_dir or args.bt_stats_dir):
        parser.error("--stats-dir and --bt-stats-dir are only used in figures mode")
    if args.bt_stats_dir and args.dataset != "bt":
        parser.error("--bt-stats-dir is only used for BT")
    if args.diagnostics and args.dataset != "portland":
        parser.error("--diagnostics is only available for Portland")

    args.output_dir = args.output_dir.resolve()
    args.data_dir = args.data_dir.resolve()
    args.stats_dir = (args.stats_dir or args.output_dir / "stats").resolve()
    args.bt_stats_dir = (args.bt_stats_dir or args.stats_dir / "bt_2_bloc_profile_stats").resolve()
    args.settings_file = args.settings_file.resolve()
    return args


def build_recipe_commands(args: argparse.Namespace) -> list[list[str]]:
    """List the primary computation and presentation commands in execution order.

    Args:
        args (argparse.Namespace): Resolved command-line options from parse_arguments.

    Returns:
        list[list[str]]: Script paths and explicit arguments, relative to the repository root.
    """
    output = ["--output-dir", str(args.output_dir)]
    inputs = ["--data-dir", str(args.data_dir)]
    seed = ["--seed", str(args.seed)]
    workers = ["--n-jobs", str(args.n_jobs)]
    figures = ["--stats-dir", str(args.stats_dir), *output]
    bt_figures = ["--bt-stats-dir", str(args.bt_stats_dir), "--n-seats", str(args.n_seats), *output]
    commands = []

    if args.mode != "figures":
        if args.dataset == "bt":
            commands.extend(
                [
                    "pipelines/bradley_terry/collect_metrics.py",
                    "--settings-file",
                    str(args.settings_file),
                    "--n-seats",
                    str(args.n_seats),
                    "--election-type",
                    rule,
                    *workers,
                    *seed,
                    *output,
                ]
                for rule in RULE_ORDER
            )
        elif args.dataset == "scottish":
            commands.append(
                ["pipelines/scottish/collect_metrics.py", *inputs, *workers, *seed, *output]
            )
        else:
            dataset = "new_york" if args.dataset == "ny" else "portland"
            commands.append([f"pipelines/{dataset}/collect_metrics.py", *inputs, *seed, *output])

    if args.mode != "stats":
        if args.dataset == "bt":
            commands.append(["pipelines/bradley_terry/plots/plot_um_iia_scatter.py", *bt_figures])
        elif args.dataset == "scottish":
            commands.append(["pipelines/scottish/plots/plot_um_iia_scatter.py", *figures])
            commands.append(["pipelines/scottish/export_metric_tables.py", *figures])
        else:
            commands.append(["scripts/export_tables.py", args.dataset, *figures])
            if args.dataset == "portland":
                commands.append(
                    [
                        "pipelines/portland/plots/plot_boost_matrix.py",
                        "--district",
                        "all",
                        *inputs,
                        *output,
                    ]
                )

    if args.diagnostics:
        commands.append(["pipelines/portland/clustering/run_short_bursts.py", *inputs])
        commands.append(["pipelines/portland/clustering/run_brute_force.py", *inputs])
    return commands


def main() -> None:
    """Print and execute the chosen dataset recipe with identical explicit arguments."""
    args = parse_arguments()
    commands = build_recipe_commands(args)

    for command in commands:
        print(
            shlex.join(
                [
                    "env",
                    "PYTHONHASHSEED=0",
                    "MPLBACKEND=Agg",
                    "uv",
                    "run",
                    "--project",
                    str(ROOT),
                    "--locked",
                    "python",
                    str(ROOT / command[0]),
                    *command[1:],
                ]
            ),
            flush=True,
        )
        if not args.dry_run:
            subprocess.run(
                [sys.executable, str(ROOT / command[0]), *command[1:]],
                cwd=ROOT,
                env={**os.environ, "PYTHONHASHSEED": "0", "MPLBACKEND": "Agg"},
                check=True,
            )


if __name__ == "__main__":
    main()
