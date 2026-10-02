"""Load Scottish metric JSON layouts into plotting tables."""

import json
from glob import escape, glob
from itertools import product
from pathlib import Path
from typing import Sequence


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
        variants (Sequence[str], optional): Aggregations to load in order. Defaults to
            ('average', 'worst_case').
        tiebreaks (Sequence[str], optional): Tiebreaks to load in order. Defaults to ('lex', 'random').

    Returns:
        dict[str, dict[str, dict[str, list[float]]]]: Nested mapping: ``rule -> candidate_count ->
            metric_key -> metric_values``.
    """
    election_type_to_metric_to_cand_count: dict[str, dict[str, dict[str, list[float]]]] = {}

    for variant, tiebreak, voting_rule in product(variants, tiebreaks, ordered_rules):
        all_output_files = glob(
            f"{escape(str(stats_dir))}/*{variant}*/{voting_rule}/*{tiebreak}_output.json"
        )
        metric_to_values: dict[str, dict[str, list[float]]] = {}
        election_type = voting_rule

        for output_file in all_output_files:
            with open(output_file, "r") as f:
                output = json.load(f)

            splits = output_file.split("/")[-1].split("__")
            metric = splits[0].removeprefix("METRIC_")
            election_type = splits[1].removeprefix("ELECTION_TYPE_").split("_")[0]
            metric_to_values[f"{metric}_{tiebreak}"] = {
                k: list(v.values()) for k, v in output.items()
            }

        if election_type not in election_type_to_metric_to_cand_count:
            election_type_to_metric_to_cand_count[election_type] = {}

        election_type_to_metric_to_cand_count[election_type] |= metric_to_values

    outputs_by_election_type = {}

    for election_type, metrics in election_type_to_metric_to_cand_count.items():
        by_candidate_count = {}

        for metric, values_by_count in metrics.items():
            for candidate_count, values in values_by_count.items():
                by_candidate_count.setdefault(candidate_count, {})[metric] = values

        outputs_by_election_type[election_type] = by_candidate_count

    return outputs_by_election_type
