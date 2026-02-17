"""Collect bootstrap confidence intervals and rectangles for Scottish elections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


TIEBREAK_PATTERN = re.compile(r"__TIEBREAK_([^_]+)_output\.json$")


def sort_candidate_size_keys(size_keys: Iterable[str]) -> list[str]:
    """Sort candidate-size keys numerically when possible.

    Args:
        size_keys (Iterable[str]): Candidate-size keys from metric JSON data.

    Returns:
        list[str]: Sorted keys where digit-only values are ordered by integer
        value and non-numeric keys are ordered lexicographically after numeric
        keys.
    """

    def _key(value: str) -> tuple[int, int | str]:
        return (0, int(value)) if value.isdigit() else (1, value)

    return sorted(size_keys, key=_key)


def parse_tiebreak_from_filename(filename: str) -> str:
    """Extract tiebreak token from a metric filename.

    Args:
        filename (str): JSON filename following metric naming conventions.

    Returns:
        str: Parsed tiebreak value (for example, ``"lex"``), or ``"unknown"``
        if parsing fails.
    """
    match = TIEBREAK_PATTERN.search(filename)
    return match.group(1) if match else "unknown"


def load_metric_json(path: Path) -> dict[str, dict[str, float]]:
    """Load one metric JSON file.

    Args:
        path (Path): Absolute path to a metric JSON file.

    Returns:
        dict[str, dict[str, float]]: Nested dictionary keyed by candidate size
        (``str``) and election id (``str``) with metric values (``float``).

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_metric_values(
    metric_data: dict[str, dict[str, float]],
    candidate_size: int | None = None,
) -> np.ndarray:
    """Extract metric values for one candidate size or pool all sizes.

    Args:
        metric_data (dict[str, dict[str, float]]): Metric values grouped by
            candidate size and election id.
        candidate_size (int | None): Specific candidate size to select. If
            ``None``, values from all candidate sizes are pooled.

    Returns:
        np.ndarray: One-dimensional float array of selected metric values.

    Raises:
        KeyError: If ``candidate_size`` is provided but not present.
        ValueError: If no values are available after filtering.
    """
    if candidate_size is None:
        values: list[float] = []
        for size_key in sort_candidate_size_keys(metric_data.keys()):
            values.extend(metric_data[size_key].values())
    else:
        key = str(candidate_size)
        if key not in metric_data:
            available = sort_candidate_size_keys(metric_data.keys())
            raise KeyError(
                f"candidate_size={candidate_size} not found. Available sizes: {available}"
            )
        values = list(metric_data[key].values())

    output = np.asarray(values, dtype=float)
    if output.size == 0:
        raise ValueError("No values available for bootstrap.")
    return output


def bootstrap_mean_percentile_ci(
    values: np.ndarray,
    n_resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Compute a percentile bootstrap confidence interval for a sample mean.

    Args:
        values (np.ndarray): One-dimensional array of observed sample values.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Two-sided error rate (for example, ``0.05`` for 95% CI).
        seed (int): Seed used by NumPy's random generator.

    Returns:
        tuple[float, float]: Lower and upper CI bounds.

    Raises:
        ValueError: If ``values`` is empty, ``n_resamples < 2``, or ``alpha``
        is not in ``(0, 1)``.
    """
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n == 0:
        raise ValueError("Cannot bootstrap an empty sample.")
    if n_resamples < 2:
        raise ValueError("n_resamples must be >= 2.")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1).")

    rng = np.random.default_rng(seed)
    boot = np.empty(n_resamples, dtype=float)

    for i in range(n_resamples):
        sample_idx = rng.integers(0, n, size=n)
        boot[i] = x[sample_idx].mean()

    boot_sorted = np.sort(boot)
    low_idx = int(np.floor(alpha * n_resamples / 2.0))
    high_idx = int(np.ceil((1.0 - alpha / 2.0) * n_resamples)) - 1

    low_idx = max(0, min(n_resamples - 1, low_idx))
    high_idx = max(0, min(n_resamples - 1, high_idx))

    return float(boot_sorted[low_idx]), float(boot_sorted[high_idx])


def bootstrap_confidence_rectangle(
    iia_data: dict[str, dict[str, float]],
    um_data: dict[str, dict[str, float]],
    candidate_size: int | None = None,
    n_resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, Any]:
    """Compute a Bonferroni-adjusted rectangle for paired IIA/UM means.

    Args:
        iia_data (dict[str, dict[str, float]]): IIA metric data keyed by
            candidate size and election id.
        um_data (dict[str, dict[str, float]]): UM metric data keyed by
            candidate size and election id.
        candidate_size (int | None): Candidate size filter. If ``None``,
            all shared sizes are pooled.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Family-wise error target for the 2D rectangle.
        seed (int): Random seed for reproducible resampling.

    Returns:
        dict[str, Any]: Rectangle output with IIA/UM intervals, pair counts,
        candidate size, and overlap metadata.

    Raises:
        ValueError: If no overlapping election ids exist after alignment.
        KeyError: If ``candidate_size`` is specified but missing in either
        metric data.
    """
    if candidate_size is None:
        size_keys = sort_candidate_size_keys(set(iia_data.keys()) & set(um_data.keys()))
    else:
        key = str(candidate_size)
        if key not in iia_data:
            raise KeyError(f"candidate_size={candidate_size} missing from IIA data.")
        if key not in um_data:
            raise KeyError(f"candidate_size={candidate_size} missing from UM data.")
        size_keys = [key]

    paired_values: list[tuple[float, float]] = []
    overlap_counts: dict[str, int] = {}

    for size_key in size_keys:
        iia_by_election = iia_data[size_key]
        um_by_election = um_data[size_key]
        common_ids = set(iia_by_election.keys()) & set(um_by_election.keys())
        overlap_counts[size_key] = len(common_ids)

        for election_id in common_ids:
            paired_values.append(
                (
                    float(iia_by_election[election_id]),
                    float(um_by_election[election_id]),
                )
            )

    paired = np.asarray(paired_values, dtype=float)
    n_pairs = len(paired)
    if n_pairs == 0:
        raise ValueError("No overlapping election IDs found across selected sizes.")

    rng = np.random.default_rng(seed)
    boot = np.empty((n_resamples, 2), dtype=float)
    for i in range(n_resamples):
        sample_idx = rng.integers(0, n_pairs, size=n_pairs)
        boot[i, :] = paired[sample_idx, :].mean(axis=0)

    q_lo = alpha / 4.0
    q_hi = 1.0 - alpha / 4.0
    iia_lower, um_lower = np.quantile(boot, q_lo, axis=0)
    iia_upper, um_upper = np.quantile(boot, q_hi, axis=0)

    return {
        "iia_L": float(iia_lower),
        "iia_U": float(iia_upper),
        "um_L": float(um_lower),
        "um_U": float(um_upper),
        "n_pairs": int(n_pairs),
        "candidate_size": candidate_size,
        "sizes_used": size_keys,
        "overlap_counts_by_size": overlap_counts,
    }


def iter_metric_json_files(
    metric_name: str,
    all_election_types: list[str],
    stats_dir: Path,
) -> Iterable[tuple[str, str, Path]]:
    """Yield metric JSON files for all rules, skipping random tiebreak files.

    Args:
        metric_name (str): Metric directory under ``stats_dir``.
        all_election_types (list[str]): Election/rule names to include.
        stats_dir (Path): Base Scottish stats directory.

    Yields:
        tuple[str, str, Path]: ``(rule, tiebreak, json_file)`` for each file.
    """
    for election_name in all_election_types:
        rule_dir = stats_dir / metric_name / election_name
        if not rule_dir.exists():
            print(f"Skipping missing rule directory: {rule_dir}")
            continue

        for json_file in sorted(rule_dir.glob("*.json")):
            tiebreak = parse_tiebreak_from_filename(json_file.name)
            if tiebreak == "random":
                continue
            yield election_name, tiebreak, json_file


def build_ci_rows_for_file(
    metric_name: str,
    election_name: str,
    tiebreak: str,
    metric_data: dict[str, dict[str, float]],
    n_resamples: int,
    alpha: float,
    seed: int,
) -> list[dict[str, Any]]:
    """Build pooled and per-size CI rows for a single metric JSON.

    Args:
        metric_name (str): Metric identifier for the output rows.
        election_name (str): Rule name.
        tiebreak (str): Tiebreak name parsed from the filename.
        metric_data (dict[str, dict[str, float]]): Metric JSON content.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Two-sided error rate.
        seed (int): RNG seed.

    Returns:
        list[dict[str, Any]]: One pooled row and one row per candidate size.

    Raises:
        ValueError: If candidate-size keys are not integer-like or bootstrap
        inputs are invalid/empty.
    """
    rows: list[dict[str, Any]] = []

    pooled_values = extract_metric_values(metric_data, candidate_size=None)
    pooled_l, pooled_u = bootstrap_mean_percentile_ci(
        values=pooled_values,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
    )
    rows.append(
        {
            "metric": metric_name,
            "rule": election_name,
            "tiebreak": tiebreak,
            "candidate_size": np.nan,
            "L": pooled_l,
            "U": pooled_u,
            "n_observations": int(pooled_values.size),
        }
    )

    for size_key in sort_candidate_size_keys(metric_data.keys()):
        candidate_size = int(size_key)
        per_size_values = extract_metric_values(
            metric_data=metric_data,
            candidate_size=candidate_size,
        )
        l_bound, u_bound = bootstrap_mean_percentile_ci(
            values=per_size_values,
            n_resamples=n_resamples,
            alpha=alpha,
            seed=seed,
        )
        rows.append(
            {
                "metric": metric_name,
                "rule": election_name,
                "tiebreak": tiebreak,
                "candidate_size": candidate_size,
                "L": l_bound,
                "U": u_bound,
                "n_observations": int(per_size_values.size),
            }
        )

    return rows


def build_rectangle_rows_for_file_pair(
    rectangle_metric_iia: str,
    rectangle_metric_um: str,
    election_name: str,
    tiebreak: str,
    iia_data: dict[str, dict[str, float]],
    um_data: dict[str, dict[str, float]],
    n_resamples: int,
    alpha: float,
    seed: int,
) -> list[dict[str, Any]]:
    """Build pooled and per-size rectangle rows for one IIA/UM file pair.

    Args:
        rectangle_metric_iia (str): IIA metric identifier.
        rectangle_metric_um (str): UM metric identifier.
        election_name (str): Rule name.
        tiebreak (str): Tiebreak name.
        iia_data (dict[str, dict[str, float]]): IIA metric JSON content.
        um_data (dict[str, dict[str, float]]): UM metric JSON content.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Family-wise error target.
        seed (int): RNG seed.

    Returns:
        list[dict[str, Any]]: One pooled row and one row per candidate size.

    Raises:
        ValueError: If candidate-size keys are not integer-like, no
        overlapping election ids are found, or bootstrap inputs are invalid.
    """
    rows: list[dict[str, Any]] = []
    size_keys = sort_candidate_size_keys(set(iia_data.keys()) & set(um_data.keys()))

    pooled_rectangle_data = bootstrap_confidence_rectangle(
        iia_data=iia_data,
        um_data=um_data,
        candidate_size=None,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
    )
    rows.append(
        {
            "metric_iia": rectangle_metric_iia,
            "metric_um": rectangle_metric_um,
            "rule": election_name,
            "tiebreak": tiebreak,
            "candidate_size": np.nan,
            "iia_L": pooled_rectangle_data["iia_L"],
            "iia_U": pooled_rectangle_data["iia_U"],
            "um_L": pooled_rectangle_data["um_L"],
            "um_U": pooled_rectangle_data["um_U"],
            "n_pairs": pooled_rectangle_data["n_pairs"],
            "sizes_used": json.dumps(pooled_rectangle_data["sizes_used"]),
            "overlap_counts_by_size": json.dumps(
                pooled_rectangle_data["overlap_counts_by_size"]
            ),
        }
    )

    for size_key in size_keys:
        rectangle_data = bootstrap_confidence_rectangle(
            iia_data=iia_data,
            um_data=um_data,
            candidate_size=int(size_key),
            n_resamples=n_resamples,
            alpha=alpha,
            seed=seed,
        )
        rows.append(
            {
                "metric_iia": rectangle_metric_iia,
                "metric_um": rectangle_metric_um,
                "rule": election_name,
                "tiebreak": tiebreak,
                "candidate_size": int(size_key),
                "iia_L": rectangle_data["iia_L"],
                "iia_U": rectangle_data["iia_U"],
                "um_L": rectangle_data["um_L"],
                "um_U": rectangle_data["um_U"],
                "n_pairs": rectangle_data["n_pairs"],
                "sizes_used": json.dumps(rectangle_data["sizes_used"]),
                "overlap_counts_by_size": json.dumps(
                    rectangle_data["overlap_counts_by_size"]
                ),
            }
        )

    return rows


def run_bootstrap_ci(
    ci_metrics: list[str],
    all_election_types: list[str],
    stats_dir: Path,
    n_resamples: int,
    alpha: float,
    seed: int,
    output_folder: Path,
) -> None:
    """Collect and save bootstrap CI CSVs for selected metrics.

    Args:
        ci_metrics (list[str]): Metric directory names to process.
        all_election_types (list[str]): Election/rule names to include.
        stats_dir (Path): Base Scottish stats directory.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Two-sided error rate.
        seed (int): RNG seed.
        output_folder (Path): Output directory for generated CI CSV files.

    Returns:
        None: Writes one CSV per metric to ``output_folder``.

    Raises:
        ValueError: If no CI rows are generated for a requested metric.
    """
    for metric_for_cis in ci_metrics:
        ci_rows: list[dict[str, Any]] = []

        for election_name, tiebreak, json_file in iter_metric_json_files(
            metric_name=metric_for_cis,
            all_election_types=all_election_types,
            stats_dir=stats_dir,
        ):
            metric_data = load_metric_json(json_file)
            ci_rows.extend(
                build_ci_rows_for_file(
                    metric_name=metric_for_cis,
                    election_name=election_name,
                    tiebreak=tiebreak,
                    metric_data=metric_data,
                    n_resamples=n_resamples,
                    alpha=alpha,
                    seed=seed,
                )
            )

        ci_df = pd.DataFrame(ci_rows)
        if ci_df.empty:
            raise ValueError(f"No CI rows generated for {metric_for_cis}.")

        ci_df = ci_df.sort_values(
            ["rule", "tiebreak", "candidate_size"], na_position="first"
        )
        ci_output_file = output_folder / f"bootstrap_cis_{metric_for_cis}.csv"
        ci_df.to_csv(ci_output_file, index=False)
        print(f"Saved bootstrap CIs: {ci_output_file}")


def run_bootstrap_rectangle(
    rectangle_metric_pairs: list[tuple[str, str]],
    all_election_types: list[str],
    stats_dir: Path,
    n_resamples: int,
    alpha: float,
    seed: int,
    output_folder: Path,
) -> None:
    """Collect and save bootstrap rectangle CSVs for selected metric pairs.

    Args:
        rectangle_metric_pairs (list[tuple[str, str]]): Pairs of
            ``(metric_iia, metric_um)`` to process.
        all_election_types (list[str]): Election/rule names to include.
        stats_dir (Path): Base Scottish stats directory.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Family-wise error target for each rectangle.
        seed (int): RNG seed.
        output_folder (Path): Output directory for generated rectangle CSV
            files.

    Returns:
        None: Writes one rectangle CSV per metric pair to ``output_folder``.

    Raises:
        ValueError: If no rectangle rows are generated for a requested metric
        pair.
    """
    for rectangle_metric_iia, rectangle_metric_um in rectangle_metric_pairs:
        rectangle_rows: list[dict[str, Any]] = []

        for election_name, tiebreak, iia_file in iter_metric_json_files(
            metric_name=rectangle_metric_iia,
            all_election_types=all_election_types,
            stats_dir=stats_dir,
        ):
            um_file = (
                stats_dir
                / rectangle_metric_um
                / election_name
                / (
                    f"METRIC_{rectangle_metric_um}"
                    f"__ELECTION_TYPE_{election_name}"
                    f"__TIEBREAK_{tiebreak}_output.json"
                )
            )

            if not um_file.exists():
                print("Skipping missing rectangle input:", um_file)
                continue

            iia_data = load_metric_json(iia_file)
            um_data = load_metric_json(um_file)
            rectangle_rows.extend(
                build_rectangle_rows_for_file_pair(
                    rectangle_metric_iia=rectangle_metric_iia,
                    rectangle_metric_um=rectangle_metric_um,
                    election_name=election_name,
                    tiebreak=tiebreak,
                    iia_data=iia_data,
                    um_data=um_data,
                    n_resamples=n_resamples,
                    alpha=alpha,
                    seed=seed,
                )
            )

        rectangle_df = pd.DataFrame(rectangle_rows)
        if rectangle_df.empty:
            raise ValueError(
                f"No rectangle rows generated for {rectangle_metric_iia} vs {rectangle_metric_um}."
            )

        rectangle_df = rectangle_df.sort_values(
            ["rule", "tiebreak", "candidate_size"],
            na_position="first",
        )
        rectangle_output_file = (
            output_folder
            / f"bootstrap_rectangles_{rectangle_metric_iia}_vs_{rectangle_metric_um}.csv"
        )
        rectangle_df.to_csv(rectangle_output_file, index=False)
        print(f"Saved confidence rectangles: {rectangle_output_file}")


if __name__ == "__main__":
    # Defaults chosen to match the bootstrap notebook experiments.
    ci_metrics = [
        "sigma_IIA_average",
        "sigma_IIA_winner_set_average",
        "sigma_UM_worst_case_asin",
        "sigma_UM_winner_set_worst_case_asin",
    ]

    rectangle_metric_pairs = [
        ("sigma_IIA_average", "sigma_UM_worst_case_asin"),
        ("sigma_IIA_winner_set_average", "sigma_UM_winner_set_worst_case_asin"),
    ]

    n_resamples = 10000
    alpha = 0.05
    seed = 0

    all_election_types = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]

    top_dir = Path(__file__).resolve().parents[2]
    stats_dir = top_dir / "stats" / "scottish_stats"

    output_folder = stats_dir / "bootstrap"
    output_folder.mkdir(parents=True, exist_ok=True)

    # =============================
    # Bootstrap confidence intervals
    # =============================
    run_bootstrap_ci(
        ci_metrics=ci_metrics,
        all_election_types=all_election_types,
        stats_dir=stats_dir,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
        output_folder=output_folder,
    )

    # ===========================
    # Bootstrap rectangle bounds
    # ===========================

    run_bootstrap_rectangle(
        rectangle_metric_pairs=rectangle_metric_pairs,
        all_election_types=all_election_types,
        stats_dir=stats_dir,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
        output_folder=output_folder,
    )
