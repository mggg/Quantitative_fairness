"""Load Scottish metric JSON layouts into plotting tables."""

import json
from collections.abc import Mapping, Sequence
from glob import escape, glob
from itertools import product
from pathlib import Path
from typing import cast

import pandas as pd


def build_metric_table(
    outputs_by_rule: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    n_cands: int,
    metric: str,
) -> pd.DataFrame:
    """Build score columns in voting-rule order for a fixed candidate count.

    Args:
        outputs_by_rule (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Scores keyed by
            rule, candidate-count string, and metric key.
        n_cands (int): Candidate count to extract.
        metric (str): Metric key to select.

    Returns:
        pd.DataFrame: Rules as columns and observations as rows, padding shorter columns with NaN.
    """
    scores_by_rule = [
        metrics_by_count[str(n_cands)][metric] for metrics_by_count in outputs_by_rule.values()
    ]

    return pd.DataFrame(scores_by_rule, index=list(outputs_by_rule)).T


def build_boxplot_table(
    outputs_by_rule: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    candidate_counts: Sequence[int],
    metric: str,
    *,
    borda_only: bool = False,
) -> pd.DataFrame:
    """Build rule, value, and candidate-count columns in the requested plotting order.

    Args:
        outputs_by_rule (Mapping[str, Mapping[str, Mapping[str, list[float]]]]): Scores keyed by
            rule, candidate-count string, and metric key.
        candidate_counts (Sequence[int]): Candidate counts in display order.
        metric (str): Metric key to select.
        borda_only (bool, optional): Retain only Borda rows after preparing all rules.
            Defaults to False.

    Returns:
        pd.DataFrame: One row per observation, retaining NaN padding for shorter score lists.

    Raises:
        ValueError: No candidate counts were supplied.
        KeyError: A requested candidate count or metric is missing.
    """
    metric_tables = []

    for n_cands in candidate_counts:
        metric_values_df = build_metric_table(outputs_by_rule, n_cands, metric)
        metric_values_df = metric_values_df.melt(var_name="rule", value_name="value")
        metric_values_df["n_cands"] = n_cands

        if borda_only:
            metric_values_df = metric_values_df[metric_values_df["rule"] == "borda"]

        metric_tables.append(metric_values_df)

    return pd.concat(metric_tables, ignore_index=True)


def export_aggregate_tables(
    stat_file_base_dir: str | Path,
    ordered_rules: Sequence[str],
    n_cand_list: Sequence[int],
    variant: str,
    tiebreak: str,
    *,
    output_root: Path,
) -> None:
    """Export aggregate Scottish statistics ordered by rule and candidate count.

    Args:
        stat_file_base_dir (str | Path): Base directory containing aggregate metric JSON files.
        ordered_rules (Sequence[str]): Voting rules in display order.
        n_cand_list (Sequence[int]): Candidate counts in display order.
        variant (str): Output filename token; input files are not filtered by it.
        tiebreak (str): Output filename token; input files are not filtered by it.
        output_root (Path): Run root containing stats, plots, and tables.
    """
    stats_by_rule = {}

    stats_paths = glob(f"{escape(str(stat_file_base_dir))}/*stats.json")
    for path in stats_paths:
        stats_path = Path(path)
        with stats_path.open() as stats_file:
            statistics = json.load(stats_file)

        election_type = stats_path.name.split("_")[0]
        stats_by_rule[election_type] = statistics

    aggregate_statistics_df = pd.concat(
        {rule: pd.DataFrame(statistics).T for rule, statistics in stats_by_rule.items()},
        names=["rule", "n_cands"],
    )
    index = cast(pd.MultiIndex, aggregate_statistics_df.index)
    aggregate_statistics_df.index = index.set_levels(index.levels[1].astype(int), level="n_cands")
    aggregate_statistics_df = aggregate_statistics_df.reindex(
        pd.MultiIndex.from_product(
            [list(ordered_rules), list(n_cand_list)], names=["rule", "n_cands"]
        )
    )

    output_dir = output_root / "stats" / "scottish_stats"
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_statistics_df.to_csv(output_dir / f"scottish_stats_{variant}_{tiebreak}.csv")


def load_outputs_by_election_type(
    stats_dir: Path,
    ordered_rules: Sequence[str],
    *,
    variants: Sequence[str] = ("average", "worst_case"),
    tiebreaks: Sequence[str] = ("lex", "random"),
) -> dict[str, dict[str, dict[str, list[float]]]]:
    """Load Scottish metric outputs grouped by rule and candidate size.

    Args:
        stats_dir (Path): Base directory containing Scottish metric JSON outputs.
        ordered_rules (Sequence[str]): Rules to include.
        variants (Sequence[str], optional): Aggregations to load in order. Defaults to ('average',
            'worst_case').
        tiebreaks (Sequence[str], optional): Tiebreaks to load in order. Defaults to ('lex',
            'random').

    Returns:
        dict[str, dict[str, dict[str, list[float]]]]: Nested mapping: ``rule -> candidate_count ->
            metric_key -> metric_values``.
    """
    metrics_by_rule: dict[str, dict[str, dict[str, list[float]]]] = {}

    for variant, tiebreak, voting_rule in product(variants, tiebreaks, ordered_rules):
        all_output_files = glob(
            f"{escape(str(stats_dir))}/*{variant}*/{voting_rule}/*{tiebreak}_output.json"
        )
        metric_to_values: dict[str, dict[str, list[float]]] = {}
        election_type = voting_rule

        for output_file in all_output_files:
            with open(output_file) as metric_file:
                output = json.load(metric_file)

            splits = Path(output_file).name.split("__")
            metric = splits[0].removeprefix("METRIC_")
            election_type = splits[1].removeprefix("ELECTION_TYPE_").split("_")[0]
            metric_to_values[f"{metric}_{tiebreak}"] = {
                candidate_count: list(election_scores.values())
                for candidate_count, election_scores in output.items()
            }

        if election_type not in metrics_by_rule:
            metrics_by_rule[election_type] = {}

        metrics_by_rule[election_type] |= metric_to_values

    outputs_by_election_type = {}

    for election_type, metrics in metrics_by_rule.items():
        by_candidate_count = {}

        for metric, values_by_count in metrics.items():
            for candidate_count, values in values_by_count.items():
                by_candidate_count.setdefault(candidate_count, {})[metric] = values

        outputs_by_election_type[election_type] = by_candidate_count

    return outputs_by_election_type
