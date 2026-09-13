"""Check that every maintained recipe references runnable scripts without writing during planning."""

import sys
from itertools import product
from pathlib import Path

import pytest

from scripts.replicate import ROOT, build_recipe_commands, parse_arguments


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
