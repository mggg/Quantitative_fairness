"""Check that every maintained recipe references runnable scripts without writing during planning."""

import subprocess
import sys
from itertools import product
from pathlib import Path

import pytest

from scripts.replicate import ROOT, build_recipe_commands, parse_arguments


def test_default_recipe_paths_follow_the_repository_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(sys, "argv", ["replicate.py", "bt", "--dry-run"])

    args = parse_arguments()

    assert ROOT == repository_root
    assert args.data_dir == repository_root / "data"
    assert args.output_dir == repository_root
    assert args.stats_dir == repository_root / "stats"
    assert args.settings_file == repository_root / "code/config/bt_profiles.txt"
    assert args.settings_file.is_file()


@pytest.mark.parametrize("dataset", ["ny", "portland", "scottish", "bt"])
def test_shell_runners_resolve_the_project_from_another_directory(
    dataset: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uv = tmp_path / "uv"
    uv.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")

    result = subprocess.run(
        ["bash", str(ROOT / f"scripts/run_{dataset}_pipeline.sh"), "--dry-run"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.splitlines() == [
        "run",
        "--project",
        str(ROOT),
        "--locked",
        "python",
        str(ROOT / "scripts/replicate.py"),
        dataset,
        "--dry-run",
    ]


def test_all_recipe_modes_reference_existing_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "new-run"
    for dataset, mode in product(("ny", "portland", "scottish", "bt"), ("stats", "figures", "all")):
        arguments = [
            "replicate.py",
            dataset,
            "--mode",
            mode,
            "--output-dir",
            str(output),
            "--dry-run",
        ]
        if dataset == "portland":
            arguments.append("--diagnostics")
        monkeypatch.setattr(sys, "argv", arguments)
        commands = build_recipe_commands(parse_arguments())

        assert commands
        assert all((ROOT / command[0]).is_file() for command in commands)
        assert not output.exists()
