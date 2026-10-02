"""Check that protected writes preserve existing data and never publish partial results."""

import subprocess
from pathlib import Path

import pytest

from scripts import fetch_data
from voting_metrics_main_code.replication import new_data_file


@pytest.mark.parametrize("destination_kind", ["file", "symlink", "dangling_symlink"])
def test_data_files_require_manual_removal_before_replacement(
    tmp_path: Path, destination_kind: str
) -> None:
    original = tmp_path / "original.json"
    original.write_text("preserved")
    destination = original
    if destination_kind != "file":
        destination = tmp_path / "result.json"
        destination.symlink_to(
            original if destination_kind == "symlink" else tmp_path / "missing.json"
        )

    with pytest.raises(FileExistsError, match="manually"):
        with new_data_file(destination) as temporary:
            temporary.write_text("replacement")

    assert original.read_text() == "preserved"
    assert not (tmp_path / "missing.json").exists()


def test_data_publication_preserves_a_result_created_during_computation(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    with pytest.raises(FileExistsError, match="manually"):
        with new_data_file(destination) as temporary:
            temporary.write_text("this run")
            destination.write_text("concurrent run")

    assert destination.read_text() == "concurrent run"
    assert list(tmp_path.iterdir()) == [destination]


def test_failed_data_writes_leave_no_partial_result(tmp_path: Path) -> None:
    destination = tmp_path / "result.json"
    with pytest.raises(RuntimeError):
        with new_data_file(destination) as temporary:
            temporary.write_text("incomplete")
            raise RuntimeError("calculation failed")

    assert not list(tmp_path.iterdir())


def test_failed_scottish_checkout_leaves_no_partial_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "scot-elex"

    def fail_checkout(command: list[str], *, check: bool) -> None:
        if command[1] == "clone":
            checkout = Path(command[-1])
            checkout.mkdir()
            (checkout / "incomplete.csv").write_text("partial checkout")
            return

        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(fetch_data.subprocess, "run", fail_checkout)

    with pytest.raises(subprocess.CalledProcessError):
        fetch_data.fetch_scottish_data(destination)

    assert not list(tmp_path.iterdir())
