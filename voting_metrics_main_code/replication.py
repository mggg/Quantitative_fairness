"""Shared input paths, generated output paths, and reproducible task seeds."""

import hashlib
import os
import random
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("QF_DATA_DIR", ROOT / "data")).resolve()
RESULTS_DIR = Path(os.environ.get("QF_RESULTS_DIR", ROOT / "results/generated")).resolve()


def check_output_directory(path: Path) -> Path:
    """Keep new outputs outside existing research trees, including symlink targets."""
    path = path.resolve()
    for name in ("data", "stats", "plots", "paper", "dev_files", "notebooks", "other_files"):
        protected = (ROOT / name).resolve()
        if path == protected or protected in path.parents or path in protected.parents:
            raise ValueError(f"Output directory overlaps preserved research files: {path}")
    if path == DATA_DIR or DATA_DIR in path.parents or path in DATA_DIR.parents:
        raise ValueError(f"Output directory overlaps input data: {path}")
    for directory, directories, files in os.walk(path, followlinks=False):
        for name in directories + files:
            entry = Path(directory) / name
            if entry.is_symlink():
                raise ValueError(f"Output tree contains a symlink: {entry}")
    return path


check_output_directory(RESULTS_DIR)
STATS_OUTPUT = RESULTS_DIR / "stats"
PLOTS_DIR = RESULTS_DIR / "plots"
STATS_INPUT = Path(os.environ.get("QF_STATS_DIR", STATS_OUTPUT)).resolve()
BT_STATS_INPUT = Path(
    os.environ.get("QF_BT_STATS_DIR", STATS_INPUT / "bt_2_bloc_profile_stats")
).resolve()
N_JOBS = int(os.environ.get("QF_N_JOBS", "1"))


def seed_task(*identity: object) -> None:
    """Seed each task independently of worker count, scheduling, and resume order."""
    key = repr((int(os.environ.get("QF_SEED", "0")), identity)).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:4], "big")
    random.seed(seed)
    np.random.seed(seed)
