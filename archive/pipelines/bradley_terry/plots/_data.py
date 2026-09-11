"""Load BT metric arrays and per-profile summary points in input-file order."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import numpy as np


def load_metric_summaries(
    paths: Sequence[str], statistic: Literal["std", "var"] = "std"
) -> list[list[float]]:
    """Return the mean and selected dispersion for each metric JSON array.

    Args:
        paths (Sequence[str]): Metric JSON paths in the desired summary order.
        statistic (Literal['std', 'var'], optional): Population dispersion statistic to pair with
            each mean. Defaults to 'std'.

    Returns:
        list[list[float]]: One [mean, dispersion] pair per input file, in the same order.

    Raises:
        ValueError: The dispersion statistic is neither 'std' nor 'var'.
        FileNotFoundError: An input file does not exist.
        json.JSONDecodeError: An input file is not valid JSON.
    """
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
    """Concatenate metric arrays without changing file or observation order.

    Args:
        paths (Sequence[str]): Metric JSON paths in concatenation order.

    Returns:
        list[float]: Concatenated scores in file order and then observation order.

    Raises:
        FileNotFoundError: An input file does not exist.
        json.JSONDecodeError: An input file is not valid JSON.
    """
    samples = []

    for path in paths:
        with open(path) as source:
            samples.extend(json.load(source))

    return samples


def find_metric_files(
    stats_root: Path,
    metric: str,
    variant: str,
    interpolation: str,
    *,
    n_seats: int = 3,
    rule: str | None = None,
    tiebreak: str = "lex",
    candidate_counts: tuple[int, int] | None = None,
    bloc_proportion: float | None = None,
    alpha: tuple[float, float, float, float] | None = None,
    cohesion: tuple[float, float] | None = None,
) -> list[str]:
    """Select preserved BT result files by their encoded experiment settings.

    Args:
        stats_root (Path): Exact two-bloc statistics tree containing seat-count directories.
        metric (str): Metric function name encoded in each result filename.
        variant (str): Aggregation variant.
        interpolation (str): Interpolation name, or the string 'None' for IIA.
        n_seats (int, optional): Seat count. Defaults to 3.
        rule (str | None, optional): Voting rule; None includes all rules. Defaults to None.
        tiebreak (str, optional): Tie-breaking method. Defaults to 'lex'.
        candidate_counts (tuple[int, int] | None, optional): Bloc sizes; None includes all.
        bloc_proportion (float | None, optional): B-bloc proportion; None includes all.
        alpha (tuple[float, float, float, float] | None, optional): Dirichlet parameters;
            None includes all combinations.
        cohesion (tuple[float, float] | None, optional): Bloc cohesions; None includes all.

    Returns:
        list[str]: Matching paths in sorted order. The printed selection identifies their source.

    Raises:
        FileNotFoundError: The requested experiment has no saved result files.
        ValueError: The seat count is not positive.
    """
    if n_seats < 1:
        raise ValueError("n_seats must be positive")

    candidates = "*" if candidate_counts is None else "_".join(f"{n:02d}" for n in candidate_counts)
    proportion = "*" if bloc_proportion is None else f"{bloc_proportion:.1f}"
    alphas = "*" if alpha is None else ",".join(f"{value:.2f}" for value in alpha)
    cohesions = "*" if cohesion is None else ",".join(f"{value:.2f}" for value in cohesion)
    filename = (
        f"METRIC_{metric}__VARIANT_{variant}__INTERP_{interpolation}"
        f"__NCANDS_({candidates})__SEATS_{n_seats}__BPROP_{proportion}"
        f"__ALPHA_({alphas})__COHESION_({cohesions})"
        f"__TYPE_{rule or '*'}__TIEBREAK_{tiebreak}.json"
    )
    pattern = f"{n_seats}_seats/{metric}/*/*/{filename}"
    selection = stats_root / pattern
    paths = sorted(str(path) for path in stats_root.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No saved BT results match: {selection}")

    print(f"Selected {len(paths)} result files: {selection}")
    return paths
