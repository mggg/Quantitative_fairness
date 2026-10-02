"""Rebuild the New York mayoral profile from the July 17, 2025 CVR workbooks."""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from votekit import RankProfile
from votekit.cleaning import (
    clean_rank_profile,
    remove_and_condense_rank_profile,
    remove_repeat_cands_rank_profile,
)
from votekit.cvr_loaders import load_ranking_csv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voting_metrics_main_code.replication import ROOT, new_data_file

CHOICE_COLUMNS = [
    "DEM Mayor Choice 1 of 5 Citywide (026916)",
    "DEM Mayor Choice 2 of 5 Citywide (226916)",
    "DEM Mayor Choice 3 of 5 Citywide (326916)",
    "DEM Mayor Choice 4 of 5 Citywide (426916)",
    "DEM Mayor Choice 5 of 5 Citywide (526916)",
]
CANDIDATE_WORKBOOK = "Primary Election 2025 - 06-24-2025_CandidacyID_To_Name.xlsx"


def load_mayoral_ballots(input_dir: Path) -> pd.DataFrame:
    """Read the five mayoral choices and map candidacy IDs to ballot names.

    Args:
        input_dir (Path): Extracted July 17, 2025 CVR directory, including the candidate workbook.

    Returns:
        pd.DataFrame: Named mayoral choices in sorted workbook order, preserving vote markers.

    Raises:
        FileNotFoundError: No ballot workbooks or candidate mapping workbook is available.
        ValueError: A ballot workbook lacks the five mayoral choice columns.
    """
    ballot_paths = sorted(input_dir.glob("2025*V1*.xlsx"))
    if not ballot_paths:
        raise FileNotFoundError(f"No 2025 CVR ballot workbooks found in {input_dir}")

    candidates_df = pd.read_excel(
        input_dir / CANDIDATE_WORKBOOK,
        usecols=["CandidacyID", "DefaultBallotName"],
        dtype={"CandidacyID": str},
        engine="openpyxl",
    )
    candidate_names = candidates_df.set_index("CandidacyID")["DefaultBallotName"].to_dict()
    ballot_tables = [
        pd.read_excel(path, usecols=CHOICE_COLUMNS, dtype=str, engine="openpyxl")
        for path in ballot_paths
    ]
    ballots_df = pd.concat(ballot_tables, ignore_index=True)

    return ballots_df[CHOICE_COLUMNS].replace(candidate_names)


def truncate_past_overvote(ranking: tuple[frozenset[str], ...]) -> tuple[frozenset[str], ...]:
    """Discard the first overvote and all later choices, retaining the ranking's padded length."""
    truncated = []
    for candidates in ranking:
        if candidates == frozenset({"overvote"}):
            break
        truncated.append(candidates)

    truncated.extend([frozenset({"~"})] * (len(ranking) - len(truncated)))
    return tuple(truncated)


def rebuild_ny_profile(input_dir: Path, output_root: Path) -> None:
    """Build the cleaned mayoral profile without replacing a saved profile.

    Overvotes truncate ballots, repeated candidates retain their first mention, and undervotes
    are condensed away. Write-ins remain candidates, matching the supplied cleaned profile.

    Args:
        input_dir (Path): Extracted July 17, 2025 CVR workbooks.
        output_root (Path): Run root containing the rebuilt data directory.

    Raises:
        FileExistsError: The cleaned profile already exists at its destination.
        OSError: A source workbook cannot be read or the cleaned profile cannot be written.
    """
    destination = output_root / "data/NY_mayor_cleaned_votekit.csv"
    with new_data_file(destination) as temporary_file:
        ballots_df = load_mayoral_ballots(input_dir)
        with TemporaryDirectory(prefix=".ny-cvr-", dir=temporary_file.parent) as temporary:
            raw_csv = Path(temporary) / "mayoral_ballots.csv"
            ballots_df.to_csv(raw_csv, index=False)
            profile = load_ranking_csv(
                str(raw_csv), rank_cols=[0, 1, 2, 3, 4], header_row=0, print_profile=False
            )

        profile = clean_rank_profile(profile, truncate_past_overvote)
        profile = remove_repeat_cands_rank_profile(profile)
        profile = remove_and_condense_rank_profile(["undervote"], profile)
        profile = RankProfile(
            df=profile.df,
            max_ranking_length=len(CHOICE_COLUMNS),
            candidates=[candidate for candidate in profile.candidates if candidate != "overvote"],
        )
        profile.to_csv(temporary_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/NY_primary_data")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Run root for rebuilt data")
    args = parser.parse_args()
    rebuild_ny_profile(args.input_dir.resolve(), args.output_dir.resolve())
