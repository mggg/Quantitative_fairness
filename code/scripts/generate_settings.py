"""List BT profile folders in stable order using repository-relative paths."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    """Write a sorted profile-folder selection using the command-line input and output paths.

    Raises:
        SystemExit: CLI arguments are invalid or no profile folders match the requested root.
        OSError: The output settings file cannot be written.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-root", type=Path, default=ROOT / "data/preference_profiles")
    parser.add_argument(
        "--output", type=Path, required=True, help="Settings file to write or replace"
    )
    args = parser.parse_args()
    folders = sorted(
        folder.resolve()
        for folder in args.profile_root.glob("*/b_proportion_*")
        if folder.is_dir() and any(folder.glob("*.csv"))
    )
    if not folders:
        parser.error(f"No profile folders under {args.profile_root}")

    with args.output.open("w") as settings_file:
        for folder in folders:
            listed_folder = folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder
            settings_file.write(f"{listed_folder}\n")


if __name__ == "__main__":
    main()
