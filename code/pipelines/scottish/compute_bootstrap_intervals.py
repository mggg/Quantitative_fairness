"""Collect bootstrap confidence intervals and rectangles for Scottish elections."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TypeAlias

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import RULE_ORDER
from voting_metrics_main_code.replication import ROOT

TableRow: TypeAlias = dict[str, str | int | float]

TIEBREAK_PATTERN = re.compile(r"__TIEBREAK_([^_]+)_output\.json$")


def sort_candidate_size_keys(size_keys: Iterable[str]) -> list[str]:
    """Sort candidate-size keys numerically when possible.

    Args:
        size_keys (Iterable[str]): Candidate-size keys from metric JSON data.

    Returns:
        list[str]: Sorted keys where digit-only values are ordered by integer value and non-numeric
            keys are ordered lexicographically after numeric keys.
    """

    def _key(value: str) -> tuple[int, int | str]:
        """Place digit-only candidate counts before other keys, sorting them numerically.

        Args:
            value (str): Candidate-count key to order.

        Returns:
            tuple[int, int | str]: Numeric-group marker and integer value, or text-group marker and
                key.
        """
        return (0, int(value)) if value.isdigit() else (1, value)

    return sorted(size_keys, key=_key)


def parse_tiebreak_from_filename(filename: str) -> str:
    """Extract tiebreak token from a metric filename.

    Args:
        filename (str): JSON filename following metric naming conventions.

    Returns:
        str: Parsed tiebreak value (for example, ``"lex"``), or ``"unknown"`` if parsing fails.
    """
    match = TIEBREAK_PATTERN.search(filename)

    return match.group(1) if match else "unknown"


def load_metric_json(path: Path) -> dict[str, dict[str, float]]:
    """Load one metric JSON file.

    Args:
        path (Path): Absolute path to a metric JSON file.

    Returns:
        dict[str, dict[str, float]]: Nested dictionary keyed by candidate size (``str``) and
            election id (``str``) with metric values (``float``).

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
        metric_data (dict[str, dict[str, float]]): Metric values grouped by candidate size and
            election id.
        candidate_size (int | None, optional): Specific candidate size to select. If ``None``,
            values from all candidate sizes are pooled. Defaults to None.

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
        n_resamples (int, optional): Number of bootstrap resamples. Defaults to 5000.
        alpha (float, optional): Two-sided error rate (for example, ``0.05`` for 95% CI). Defaults
            to 0.05.
        seed (int, optional): Seed used by NumPy's random generator. Defaults to 0.

    Returns:
        tuple[float, float]: Lower and upper CI bounds.

    Raises:
        ValueError: If ``values`` is empty, ``n_resamples < 2``, or ``alpha`` is not in ``(0, 1)``.
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


@dataclass(frozen=True)
class BootstrapSamples:
    """Observed IIA/UM pairs and resampled means use the same two-column order."""

    paired: np.ndarray
    bootstrap_means: np.ndarray


@dataclass(frozen=True)
class ConfidenceRectangle:
    iia_lower: float
    iia_upper: float
    um_lower: float
    um_upper: float
    n_pairs: int
    candidate_size: int | None
    overlap_counts: dict[str, int]
    samples: BootstrapSamples | None = None


def align_metric_pairs(
    iia_data: dict[str, dict[str, float]],
    um_data: dict[str, dict[str, float]],
    candidate_size: int | None,
) -> tuple[np.ndarray, dict[str, int]]:
    """Align observations by candidate count and election ID in deterministic order.

    Only shared elections contribute; overlap counts include selected sizes with no shared IDs.
    A requested size must exist in both metrics, and at least one pair must remain.

    Args:
        iia_data (dict[str, dict[str, float]]): IIA scores keyed by candidate count and election ID.
        um_data (dict[str, dict[str, float]]): UM scores keyed by candidate count and election ID.
        candidate_size (int | None): Candidate count to select; None includes all shared counts.

    Returns:
        tuple[np.ndarray, dict[str, int]]: Two-column IIA/UM observations and shared-election counts
            for each selected candidate size, both in deterministic order.

    Raises:
        KeyError: The requested candidate count is absent from either metric.
        ValueError: No shared elections remain, or a paired score cannot be converted to float.
    """
    if candidate_size is None:
        size_keys = sort_candidate_size_keys(set(iia_data) & set(um_data))
    else:
        key = str(candidate_size)
        if key not in iia_data:
            raise KeyError(f"candidate_size={candidate_size} missing from IIA data.")
        if key not in um_data:
            raise KeyError(f"candidate_size={candidate_size} missing from UM data.")
        size_keys = [key]

    paired_values = []
    overlap_counts = {}
    for size_key in size_keys:
        iia_by_election = iia_data[size_key]
        um_by_election = um_data[size_key]
        common_ids = sorted(set(iia_by_election) & set(um_by_election))
        overlap_counts[size_key] = len(common_ids)

        paired_values.extend(
            (float(iia_by_election[election_id]), float(um_by_election[election_id]))
            for election_id in common_ids
        )

    if not paired_values:
        raise ValueError("No overlapping election IDs found across selected sizes.")

    return np.asarray(paired_values, dtype=float), overlap_counts


def bootstrap_confidence_rectangle(
    iia_data: dict[str, dict[str, float]],
    um_data: dict[str, dict[str, float]],
    candidate_size: int | None = None,
    n_resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
    return_samples: bool = False,
) -> ConfidenceRectangle:
    """Compute a Bonferroni-adjusted rectangle for paired IIA/UM means.

    Args:
        iia_data (dict[str, dict[str, float]]): IIA metric data keyed by candidate size and election
            id.
        um_data (dict[str, dict[str, float]]): UM metric data keyed by candidate size and election
            id.
        candidate_size (int | None, optional): Candidate size filter. If ``None``, all shared sizes
            are pooled. Defaults to None.
        n_resamples (int, optional): Number of bootstrap resamples. Defaults to 5000.
        alpha (float, optional): Family-wise error target for the 2D rectangle. Defaults to 0.05.
        seed (int, optional): Random seed for reproducible resampling. Defaults to 0.
        return_samples (bool, optional): Include paired observations and resampled means for
            plotting. Defaults to False.

    Returns:
        ConfidenceRectangle: IIA/UM intervals, pair counts, candidate size, and
            overlap metadata.

    Raises:
        ValueError: No overlapping election IDs remain, n_resamples is below two, or alpha is
            outside (0, 1).
        KeyError: If ``candidate_size`` is specified but missing in either metric data.
    """
    if n_resamples < 2:
        raise ValueError("n_resamples must be >= 2.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1).")

    paired, overlap_counts = align_metric_pairs(iia_data, um_data, candidate_size)
    n_pairs = len(paired)

    rng = np.random.default_rng(seed)
    boot = np.empty((n_resamples, 2), dtype=float)

    for i in range(n_resamples):
        sample_idx = rng.integers(0, n_pairs, size=n_pairs)
        boot[i, :] = paired[sample_idx, :].mean(axis=0)

    q_lo = alpha / 4.0
    q_hi = 1.0 - alpha / 4.0
    iia_lower, um_lower = np.quantile(boot, q_lo, axis=0)
    iia_upper, um_upper = np.quantile(boot, q_hi, axis=0)

    return ConfidenceRectangle(
        iia_lower=float(iia_lower),
        iia_upper=float(iia_upper),
        um_lower=float(um_lower),
        um_upper=float(um_upper),
        n_pairs=n_pairs,
        candidate_size=candidate_size,
        overlap_counts=overlap_counts,
        samples=BootstrapSamples(paired, boot) if return_samples else None,
    )


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
) -> list[TableRow]:
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
        list[TableRow]: One pooled row and one row per candidate size.

    Raises:
        ValueError: If candidate-size keys are not integer-like or bootstrap inputs are
            invalid/empty.
    """
    rows: list[TableRow] = []

    sizes = sort_candidate_size_keys(metric_data)
    for candidate_size in (None, *(int(key) for key in sizes)):
        values = extract_metric_values(metric_data, candidate_size=candidate_size)
        lower, upper = bootstrap_mean_percentile_ci(values, n_resamples, alpha, seed)

        rows.append(
            {
                "metric": metric_name,
                "rule": election_name,
                "tiebreak": tiebreak,
                "candidate_size": np.nan if candidate_size is None else candidate_size,
                "L": lower,
                "U": upper,
                "n_observations": int(values.size),
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
) -> list[TableRow]:
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
        list[TableRow]: One pooled row and one row per candidate size.

    Raises:
        ValueError: If candidate-size keys are not integer-like, no overlapping election ids are
            found, or bootstrap inputs are invalid.
    """
    rows: list[TableRow] = []
    size_keys = sort_candidate_size_keys(set(iia_data.keys()) & set(um_data.keys()))

    for candidate_size in (None, *(int(key) for key in size_keys)):
        rectangle = bootstrap_confidence_rectangle(
            iia_data=iia_data,
            um_data=um_data,
            candidate_size=candidate_size,
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
                "candidate_size": np.nan if candidate_size is None else candidate_size,
                "iia_L": rectangle.iia_lower,
                "iia_U": rectangle.iia_upper,
                "um_L": rectangle.um_lower,
                "um_U": rectangle.um_upper,
                "n_pairs": rectangle.n_pairs,
                "sizes_used": json.dumps(list(rectangle.overlap_counts)),
                "overlap_counts_by_size": json.dumps(rectangle.overlap_counts),
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
        ci_rows: list[TableRow] = []

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

        ci_df = ci_df.sort_values(["rule", "tiebreak", "candidate_size"], na_position="first")
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
        rectangle_metric_pairs (list[tuple[str, str]]): Pairs of ``(metric_iia, metric_um)`` to
            process.
        all_election_types (list[str]): Election/rule names to include.
        stats_dir (Path): Base Scottish stats directory.
        n_resamples (int): Number of bootstrap resamples.
        alpha (float): Family-wise error target for each rectangle.
        seed (int): RNG seed.
        output_folder (Path): Output directory for generated rectangle CSV files.

    Returns:
        None: Writes one rectangle CSV per metric pair to ``output_folder``.

    Raises:
        ValueError: If no rectangle rows are generated for a requested metric pair.
    """
    for rectangle_metric_iia, rectangle_metric_um in rectangle_metric_pairs:
        rectangle_rows: list[TableRow] = []

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


def main(
    *,
    stats_root: Path | None = None,
    output_root: Path = ROOT,
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> None:
    """Save bootstrap intervals and paired confidence rectangles for the primary Scottish metrics.

    Args:
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root. Defaults to None.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        n_resamples (int, optional): Bootstrap resamples. Defaults to 10000.
        alpha (float, optional): Bootstrap error probability. Defaults to 0.05.
        seed (int, optional): Base seed for task streams. Defaults to 0.

    Raises:
        ValueError: A requested metric or metric pair produces no rows, or bootstrap inputs are
            invalid.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()

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

    all_election_types = list(RULE_ORDER)

    stats_dir = stats_root / "scottish_stats"

    output_folder = output_root / "stats" / "scottish_stats" / "bootstrap"
    output_folder.mkdir(parents=True, exist_ok=True)

    run_bootstrap_ci(
        ci_metrics=ci_metrics,
        all_election_types=all_election_types,
        stats_dir=stats_dir,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
        output_folder=output_folder,
    )

    run_bootstrap_rectangle(
        rectangle_metric_pairs=rectangle_metric_pairs,
        all_election_types=all_election_types,
        stats_dir=stats_dir,
        n_resamples=n_resamples,
        alpha=alpha,
        seed=seed,
        output_folder=output_folder,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n-resamples", type=int, default=10000)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()
    main(
        stats_root=args.stats_dir,
        output_root=args.output_dir,
        seed=args.seed,
        n_resamples=args.n_resamples,
        alpha=args.alpha,
    )
