"""Plot UM vs IIA scatter comparisons for BT metrics."""

import json
import sys
from glob import glob
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from pipelines.bradley_terry.plots._metrics import (
    iia_metric_list,
)

from voting_metrics_main_code.constants import (
    ALT_FONT_SIZES,
    DEFAULT_FONT_SIZE,
    RULE_COLORS as rule_color_map,
)
from voting_metrics_main_code.replication import BT_STATS_INPUT, PLOTS_DIR

plots_dir = PLOTS_DIR / "bt_plots" / "um_vs_iia_plots"


def load_paired_metrics(
    metric: str, voting_rule: str, iia_variant: str, um_variant: str, tiebreak: str
) -> tuple[list[float], list[float]]:
    iia_file_basename = (
        f"METRIC_{metric}"
        f"__VARIANT_{iia_variant}"
        f"__INTERP_None"
        f"__NCANDS_(*)"
        f"__SEATS_3"
        f"__BPROP_*"
        f"__ALPHA_(*)"
        f"__COHESION_(*)"
        f"__TYPE_{voting_rule}"
        f"__TIEBREAK_{tiebreak}"
    )

    all_files = glob(f"{BT_STATS_INPUT}/3_seats/{metric}/**/**/{iia_file_basename}.json")

    iia_data = []
    um_data = []
    for i, iia_file in enumerate(all_files):
        with open(iia_file, "r") as f:
            iia_data.extend(json.load(f))
        um_file = (
            str(Path(iia_file).relative_to(BT_STATS_INPUT))
            .replace("METRIC_sigma_IIA", "METRIC_sigma_UM")
            .replace("__INTERP_None", "__INTERP_asin")
            .replace("/sigma_IIA", "/sigma_UM")
            .replace(f"_VARIANT_{iia_variant}", f"_VARIANT_{um_variant}")
        )
        with open(BT_STATS_INPUT / um_file, "r") as f_um:
            um_data.extend(json.load(f_um))

    return iia_data, um_data


def plot_rule_comparison(metric: str, voting_rule: str) -> None:
    iia_variant = "average"
    um_variant = "worst_case"
    tiebreak = "lex"
    iia_data, um_data = load_paired_metrics(metric, voting_rule, iia_variant, um_variant, tiebreak)

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

    ax.vlines(
        0.0,
        -0.05,
        1.05,
        color="grey",
        linestyle="-",
        linewidth=1,
        zorder=-1,
        alpha=0.5,
    )
    ax.vlines(
        1.0,
        -0.05,
        1.05,
        color="grey",
        linestyle="-",
        linewidth=1,
        zorder=-1,
        alpha=0.5,
    )
    ax.hlines(
        0.0,
        -0.05,
        1.05,
        color="grey",
        linestyle="-",
        linewidth=1,
        zorder=-1,
        alpha=0.5,
    )
    ax.hlines(
        1.0,
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


def main() -> None:
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
            plot_rule_comparison(metric, voting_rule)


if __name__ == "__main__":
    main()
