"""List BT profile folders in stable order using repository-relative paths."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-root", type=Path, default=ROOT / "data/preference_profiles")
    parser.add_argument(
        "--output", type=Path, required=True, help="Settings file to write or replace"
    )
    args = parser.parse_args()
    folders = sorted(
        p.resolve()
        for p in args.profile_root.glob("*/b_proportion_*")
        if p.is_dir() and any(p.glob("*.csv"))
    )
    if not folders:
        parser.error(f"No profile folders under {args.profile_root}")
    with args.output.open("w") as handle:
        for folder in folders:
            handle.write(
                str(folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder) + "\n"
            )


if __name__ == "__main__":
    main()
