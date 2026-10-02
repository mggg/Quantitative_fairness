"""Rebuild Portland profiles from the recorded raw VoteKit CSVs."""

import argparse
import sys
from pathlib import Path

from votekit.cleaning import (
    remove_and_condense_rank_profile,
    remove_repeat_cands_rank_profile,
)
from votekit.cvr_loaders import load_ranking_csv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voting_metrics_main_code.replication import ROOT, new_data_file

PORTLAND_SOURCE_URL = (
    "https://raw.githubusercontent.com/mggg/Portland-Postmortem/"
    "c5bde0d4f2b30871573b881af0a6a10a3f386925/"
    "Restructured%20Repo/CVRs/raw_votekit_csv"
)


def rebuild_portland_profiles(input_dir: Path | None, output_root: Path) -> None:
    """Clean all four district profiles without replacing existing outputs.

    Args:
        input_dir (Path | None): Directory of raw CSVs, or None to use the recorded source URLs.
        output_root (Path): Run root containing the rebuilt data directory.

    Raises:
        FileExistsError: A cleaned profile already exists at its destination.
        OSError: A raw input cannot be retrieved or a cleaned profile cannot be written.
    """
    for district in range(1, 5):
        filename = f"Portland_D{district}_raw_votekit_format.csv"
        source = str(input_dir / filename) if input_dir else f"{PORTLAND_SOURCE_URL}/{filename}"
        destination = output_root / "data" / f"Portland_D{district}_cleaned_votekit.csv"

        with new_data_file(destination) as temporary_file:
            profile = load_ranking_csv(
                source, rank_cols=[1, 2, 3, 4, 5, 6], header_row=0, print_profile=False
            )
            profile = remove_repeat_cands_rank_profile(profile)
            profile = remove_and_condense_rank_profile(
                ["Uncertified Write In", "overvote"] + [f"Write-in-{i}" for i in range(120, 132)],
                profile,
            )
            profile.to_csv(temporary_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, help="Raw CSV directory; defaults to source URLs")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Run root for rebuilt data")
    args = parser.parse_args()
    rebuild_portland_profiles(args.input_dir, args.output_dir.resolve())
