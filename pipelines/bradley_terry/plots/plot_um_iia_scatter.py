"""Plot UM vs IIA scatter comparisons for BT metrics."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._data import find_metric_files, resolve_paired_metric_file
from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
)
from voting_metrics_main_code.constants import (
    ALT_FONT_SIZES,
    DEFAULT_FONT_SIZE,
)
from voting_metrics_main_code.constants import (
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import ROOT


def load_paired_metrics(
    metric: str,
    voting_rule: str,
    iia_variant: str,
    um_variant: str,
    tiebreak: str,
    *,
    bt_stats_root: Path,
    n_seats: int = 3,
) -> tuple[list[float], list[float]]:
    """Load IIA scores and their corresponding ASIN UM scores from matching profile settings.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        metric (str): IIA metric identifier; the UM counterpart is derived from its name.
        voting_rule (str): Voting rule name used to select statistics.
        iia_variant (str): IIA aggregation variant used to match filenames.
        um_variant (str): UM aggregation variant used to derive paired filenames.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.

    Returns:
        tuple[list[float], list[float]]: IIA scores followed by UM scores. File and observation
            order are retained; pairing assumes matching files contain profiles in the same order.

    Raises:
        FileNotFoundError: A matching UM file or selected IIA file does not exist.
        json.JSONDecodeError: A selected metric file is not valid JSON.
    """
    all_files = find_metric_files(
        bt_stats_root,
        metric,
        iia_variant,
        "None",
        n_seats=n_seats,
        rule=voting_rule,
        tiebreak=tiebreak,
    )

    iia_data = []
    um_data = []

    um_metric = {"sigma_IIA": "sigma_UM", "sigma_IIA_winner_set": "sigma_UM_winner_set"}[metric]
    for iia_file in all_files:
        um_file = resolve_paired_metric_file(Path(iia_file), um_metric, um_variant, "asin")
        with open(iia_file) as source, um_file.open() as companion:
            iia_scores = json.load(source)
            um_scores = json.load(companion)
        if len(iia_scores) != len(um_scores):
            raise ValueError(f"Paired score counts differ: {iia_file} and {um_file}")
        iia_data.extend(iia_scores)
        um_data.extend(um_scores)

    return iia_data, um_data


def plot_rule_comparison(
    metric: str,
    voting_rule: str,
    *,
    bt_stats_root: Path,
    output_root: Path,
    n_seats: int = 3,
) -> None:
    """Save worst-case UM versus average IIA scores for one rule with lexicographic tiebreaks.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path): Exact two-bloc BT statistics tree.
        output_root (Path): Run root containing stats, plots, and tables.
        metric (str): Metric identifier used in the statistics filenames.
        voting_rule (str): Voting rule name used to select statistics.
    """
    plots_dir = output_root / "plots" / "bt_plots" / "um_vs_iia_plots"

    iia_variant = "average"
    um_variant = "worst_case"
    tiebreak = "lex"
    iia_data, um_data = load_paired_metrics(
        metric,
        voting_rule,
        iia_variant,
        um_variant,
        tiebreak,
        bt_stats_root=bt_stats_root,
        n_seats=n_seats,
    )

    um_type = metric.replace("sigma_IIA", "sigma_UM")
    plot_name = (
        f"{plots_dir}/"
        f"{voting_rule}_"
        f"{um_type}_vs_"
        f"{metric}_variant_({um_variant},{iia_variant})_ntrials_{len(um_data)}_scatter_{tiebreak}.png"
    )
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    sns.set_theme(style="ticks", context="notebook", font="serif", font_scale=1.2)

    print(f"Creating plot: {plot_name} with {len(um_data)} points.")

    ax.scatter(
        um_data,
        iia_data,
        color=rule_color_map[voting_rule],
        s=100,
        alpha=0.3,
        edgecolors="none",
    )

    ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    ax.set_xlim(min(ticks) - 0.05, max(ticks) + 0.05)
    ax.set_ylim(min(ticks) - 0.05, max(ticks) + 0.05)

    ax.set_xticks(
        ticks,
        labels=[f"{tick:.1f}" for tick in ticks],
        fontsize=ALT_FONT_SIZES.get(voting_rule, DEFAULT_FONT_SIZE),
    )
    ax.set_yticks(
        ticks,
        labels=[f"{tick:.1f}" for tick in ticks],
        fontsize=ALT_FONT_SIZES.get(voting_rule, DEFAULT_FONT_SIZE),
    )

    for draw_line in (ax.vlines, ax.hlines):
        for boundary in (0.0, 1.0):
            draw_line(
                boundary,
                -0.05,
                1.05,
                color="grey",
                linestyle="-",
                linewidth=1,
                zorder=-1,
                alpha=0.5,
            )

    plt.savefig(plot_name, bbox_inches="tight", dpi=300)

    plt.close(fig)


def main(*, bt_stats_root: Path | None = None, output_root: Path = ROOT, n_seats: int = 3) -> None:
    """Save the configured BT UM-versus-IIA scatterplots for each voting rule.

    Args:
        n_seats (int, optional): Seat count in the selected BT experiment. Defaults to 3.
        bt_stats_root (Path | None, optional): Exact two-bloc BT statistics tree. None uses the
            selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    bt_stats_root = (bt_stats_root or output_root / "stats/bt_2_bloc_profile_stats").resolve()
    print(f"BT statistics: {bt_stats_root}")
    print(f"Output root: {output_root}")
    print(f"Seats: {n_seats}")

    plots_dir = output_root / "plots" / "bt_plots" / "um_vs_iia_plots"

    plots_dir.mkdir(parents=True, exist_ok=True)

    for metric in iia_metric_list:
        for voting_rule in [
            "borda",
            "stv",
            "plurality",
            "2-approval",
            "3-approval",
            "ranked-pairs",
            "random",
        ]:
            plot_rule_comparison(
                metric,
                voting_rule,
                bt_stats_root=bt_stats_root,
                output_root=output_root,
                n_seats=n_seats,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bt-stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--n-seats", type=int, default=3)
    args = parser.parse_args()
    main(bt_stats_root=args.bt_stats_dir, output_root=args.output_dir, n_seats=args.n_seats)
