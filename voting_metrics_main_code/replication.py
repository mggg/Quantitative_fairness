"""Repository root, protected data writes, and reproducible task seeds."""

import hashlib
import os
import random
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def new_data_file(path: Path) -> Generator[Path, None, None]:
    """Publish a completed data file without replacing an existing destination.

    Args:
        path (Path): Destination for a profile, preference interval dataframe, or result file.

    Yields:
        Path: Temporary path to write; published at the destination on successful exit.

    Raises:
        FileExistsError: The destination exists. Move it manually before recomputing.
        OSError: The temporary file cannot be written or linked into place.
    """
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Move the existing data file manually before recomputing: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix=".qf-write-", dir=path.parent) as temporary:
        staged = Path(temporary) / path.name
        yield staged

        # Linking publishes the complete file and fails if another writer created the destination.
        try:
            os.link(staged, path)
        except FileExistsError:
            raise FileExistsError(
                f"Move the existing data file manually before recomputing: {path}"
            ) from None


def seed_task(*identity: object, seed: int = 0) -> None:
    """Seed each task independently of worker count, scheduling, and resume order.

    Args:
        *identity (object): Stable identifiers for the experiment and individual task.
        seed (int, optional): Base seed supplied by the workflow. Defaults to 0.
    """
    key = repr((seed, identity)).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:4], "big")
    random.seed(seed)
    np.random.seed(seed)
