"""Load BT metric arrays and per-profile summary points in input-file order."""

import json
from collections.abc import Sequence
from typing import Literal

import numpy as np


def load_metric_summaries(
    paths: Sequence[str], statistic: Literal["std", "var"] = "std"
) -> list[list[float]]:
    """Return the mean and selected dispersion for each metric JSON array."""
    if statistic not in ("std", "var"):
        raise ValueError(f"Unknown dispersion statistic: {statistic}")
    dispersion = np.std if statistic == "std" else np.var

    summaries = []
    for path in paths:
        with open(path) as source:
            values = json.load(source)

        summaries.append([float(np.mean(values)), float(dispersion(values))])

    return summaries


def load_metric_samples(paths: Sequence[str]) -> list[float]:
    """Concatenate metric arrays without changing file or observation order."""
    samples = []
    for path in paths:
        with open(path) as source:
            samples.extend(json.load(source))

    return samples
