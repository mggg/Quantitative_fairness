"""Configure individual BT metrics for profile collectors."""

from collections.abc import Callable
from functools import partial
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import MetricVariant
from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_all_subset,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_all_subset,
    sigma_UM,
    sigma_UM_winner_set,
)


def configure_metric(
    metric: str, n_seats: int, variant: MetricVariant, interpolation_type: str
) -> Callable[..., float]:
    """Bind a metric's seat count and variant, adding interpolation only for UM metrics.

    Args:
        metric (str): Metric identifier used by the collector CLI.
        n_seats (int): Number of seats to elect.
        variant (MetricVariant): Aggregation variant to bind.
        interpolation_type (str): UM interpolation token; ignored for IIA metrics.

    Returns:
        Callable[..., float]: Configured metric accepting a profile and voting rule.

    Raises:
        KeyError: The metric identifier is not supported.
    """
    metric_functions = {
        "sigma_UM": sigma_UM,
        "sigma_UM_winner_set": sigma_UM_winner_set,
        "sigma_IIA": sigma_IIA,
        "sigma_IIA_all_subset": sigma_IIA_all_subset,
        "sigma_IIA_winner_set": sigma_IIA_winner_set,
        "sigma_IIA_winner_set_all_subset": sigma_IIA_winner_set_all_subset,
    }
    metric_function = metric_functions[metric]

    if metric in ("sigma_UM", "sigma_UM_winner_set"):
        return partial(
            metric_function,
            n_seats=n_seats,
            variant=variant,
            interpolation_type=interpolation_type,
        )

    return partial(metric_function, n_seats=n_seats, variant=variant)
