"""Shared voting-rule presentation and Bradley–Terry experiment settings.

Sequence order determines legend order and experiment enumeration. Analysis-specific subsets,
palettes, and metric variants remain with their callers.
"""

from typing import Literal, TypeAlias, get_args

MetricVariant: TypeAlias = Literal["average", "worst_case"]
InterpolationType: TypeAlias = Literal["asin", "odds", "linear"]

AllowedRule: TypeAlias = Literal[
    "borda", "3-approval", "2-approval", "plurality", "stv", "ranked-pairs", "random"
]
RULE_ORDER = get_args(AllowedRule)
NON_RANDOM_RULE_ORDER = RULE_ORDER[:-1]
COMPARISON_RULE_ORDER = ("borda", "stv", "plurality")

RULE_COLORS = {
    "borda": "#1460bc",  # denim
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}
RULE_LABELS = {
    "borda": "Borda",
    "3-approval": "3-Approval",
    "2-approval": "2-Approval",
    "plurality": "Plurality",
    "stv": "STV",
    "ranked-pairs": "Ranked Pairs",
    "random": "Random",
}
COMPARISON_RULE_LABELS = {rule: RULE_LABELS[rule] for rule in ("borda", "plurality", "stv")}
DEFAULT_FONT_SIZE = 24
ALT_FONT_SIZES = {"random": 16, "ranked-pairs": 16}

BT_BLOC_PROPORTIONS = (0.5, 0.6, 0.7, 0.8, 0.9)
BT_ALPHA_COMBINATIONS = (
    (1, 1, 1, 1),
    (0.5, 0.5, 0.5, 0.5),
    (2, 2, 2, 2),
    (1, 0.5, 1, 0.5),
    (1, 2, 1, 2),
    (0.5, 1, 0.5, 1),
    (2, 1, 2, 1),
)
BT_COHESION_COMBINATIONS = ((0.7, 0.7), (0.7, 0.9), (0.9, 0.7), (0.9, 0.9))
BT_CANDIDATE_COMBINATIONS = ((2, 6), (4, 4), (6, 2), (2, 8), (5, 5), (8, 2))
