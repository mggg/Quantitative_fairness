"""Configure individual BT metrics for profile collectors."""

import sys
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Literal, TypeAlias, cast, get_args

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import InterpolationType, MetricVariant
from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_random,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_all_subset,
    sigma_IIA_winner_set_random,
    sigma_UM,
    sigma_UM_winner_set,
)

UMMetricName: TypeAlias = Literal["sigma_UM", "sigma_UM_winner_set"]
IIAMetricName: TypeAlias = Literal[
    "sigma_IIA", "sigma_IIA_all_subset", "sigma_IIA_winner_set", "sigma_IIA_winner_set_all_subset"
]


@dataclass(frozen=True)
class UMMetric:
    """UM scores require an aggregation variant and an interpolation."""

    name: UMMetricName
    variant: MetricVariant
    interpolation: InterpolationType


@dataclass(frozen=True)
class IIAMetric:
    """IIA scores use an aggregation variant without interpolation."""

    name: IIAMetricName
    variant: MetricVariant


MetricSpec: TypeAlias = UMMetric | IIAMetric


def parse_metric_spec(metric: str, variant: str, interpolation: str) -> MetricSpec:
    """Validate CLI metric settings; IIA ignores the historical interpolation option."""
    if variant not in get_args(MetricVariant):
        raise ValueError(f"Unknown metric variant: {variant}")

    if metric in get_args(UMMetricName):
        if interpolation not in get_args(InterpolationType):
            raise ValueError(
                f"Invalid UM interpolation: {interpolation}; use asin, odds, or linear"
            )
        return UMMetric(
            cast(UMMetricName, metric),
            cast(MetricVariant, variant),
            cast(InterpolationType, interpolation),
        )

    if metric in get_args(IIAMetricName):
        return IIAMetric(cast(IIAMetricName, metric), cast(MetricVariant, variant))

    raise ValueError(f"Unknown metric: {metric}")


def configure_metric(
    spec: MetricSpec, n_seats: int, *, random_rule: bool = False
) -> partial[float]:
    """Bind metric parameters, using independent random rankings when requested for IIA.

    The single-removal random IIA metrics sample rankings directly. Other metrics run the
    supplied election constructor. The returned callable accepts a profile and voting rule.
    """
    if isinstance(spec, UMMetric):
        metric = sigma_UM if spec.name == "sigma_UM" else sigma_UM_winner_set
        return partial(
            metric, n_seats=n_seats, variant=spec.variant, interpolation_type=spec.interpolation
        )

    metric_functions = {
        "sigma_IIA": sigma_IIA_random if random_rule else sigma_IIA,
        "sigma_IIA_winner_set": sigma_IIA_winner_set_random
        if random_rule
        else sigma_IIA_winner_set,
        "sigma_IIA_all_subset": sigma_IIA_all_subset,
        "sigma_IIA_winner_set_all_subset": sigma_IIA_winner_set_all_subset,
    }
    return partial(metric_functions[spec.name], n_seats=n_seats, variant=spec.variant)
