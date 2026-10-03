"""Retrieve optional replication inputs without replacing existing data."""

import argparse
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOTTISH_REVISION = "304b0842b54f0fe89441757424106be8a991f57f"


def extract_profiles(archive: Path, destination: Path) -> None:
    """Extract into a temporary sibling and publish only a complete, new directory.

    Args:
        archive (Path): Compressed tar archive containing the preference_profiles directory.
        destination (Path): New directory at which to publish the extracted profiles.

    Raises:
        FileExistsError: The destination exists before extraction or appears before publication.
        ValueError: The archive contains unexpected paths or entry types, or contains no profile
            CSVs.
        tarfile.TarError: The archive cannot be read or an entry fails the extraction filter.
        OSError: The archive cannot be opened or its files cannot be extracted or published.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Preserving existing directory: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".qf-extract-", dir=destination.parent) as temporary:
        with tarfile.open(archive, "r:xz") as handle:
            for member in handle:
                parts = Path(member.name).parts
                if not parts or parts[0] != "preference_profiles" or ".." in parts:
                    raise ValueError(f"Unexpected archive path: {member.name}")
                if not (member.isfile() or member.isdir()):
                    raise ValueError(f"Unexpected archive entry: {member.name}")

                handle.extract(member, temporary, filter="data")

        extracted = Path(temporary) / "preference_profiles"
        if not any(extracted.rglob("*.csv")):
            raise ValueError("Archive contains no preference profiles")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Preserving existing directory: {destination}")

        extracted.rename(destination)


def fetch_scottish_data(destination: Path) -> None:
    """Clone the recorded Scottish dataset revision and publish its completed checkout.

    Args:
        destination (Path): New dataset directory whose parent already exists.

    Raises:
        FileExistsError: The destination exists when the checkout is ready to publish.
        subprocess.CalledProcessError: Cloning or checking out the recorded revision fails.
        OSError: The temporary checkout cannot be created or published.
    """
    with tempfile.TemporaryDirectory(prefix=".qf-fetch-", dir=destination.parent) as temporary:
        checkout = Path(temporary) / "scot-elex"
        subprocess.run(
            [
                "git",
                "clone",
                "--no-checkout",
                "https://github.com/mggg/scot-elex.git",
                str(checkout),
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(checkout), "checkout", "--detach", SCOTTISH_REVISION], check=True
        )

        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Preserving existing data at {destination}")

        checkout.rename(destination)


def main() -> None:
    """Retrieve the selected dataset using the command-line destination and provenance settings.

    Raises:
        SystemExit: CLI options, destination selection, or archived-input checks are invalid.
        FileExistsError: A destination appears before the retrieved data can be published.
        subprocess.CalledProcessError: Cloning or checking out the Scottish dataset fails.
        OSError: A required input cannot be read or the retrieved data cannot be written.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("bt", "scottish"))
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    destination = args.destination or ROOT / "data" / (
        "preference_profiles" if args.dataset == "bt" else "scot-elex"
    )
    if destination.exists() or destination.is_symlink():
        parser.error(
            f"Preserving existing data at {destination}; use another --destination if needed"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    if args.dataset == "scottish":
        fetch_scottish_data(destination)
        return

    archive = ROOT / "data/preference_profiles.tar.xz"
    with archive.open("rb") as archive_file:
        if archive_file.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
            parser.error(
                "BT archive is an LFS pointer. Run git lfs pull --include=data/preference_profiles.tar.xz"
            )

    extract_profiles(archive, destination)


if __name__ == "__main__":
    main()
