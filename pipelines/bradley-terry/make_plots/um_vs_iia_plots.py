from pathlib import Path
from glob import glob
import json
import seaborn as sns
import matplotlib.pyplot as plt

# Imports from this folder
from metric_lists import (
    iia_metric_list,
)


script_dir = Path(__file__).parent
top_dir = script_dir.parents[2].resolve()
plots_dir = top_dir / "plots" / "bt_plots" / "um_vs_iia_plots"

rule_color_map = {
    "borda": "#1460bc",  # denim
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}
titles = {
    "borda": "Borda",
    "plurality": "Plurality",
    "stv": "STV",
}

tiebreak = "lex"

# bprop = "*"
# voting_rule = "*"
# for (
#     metric,
#     iia_variant,
#     um_variant,
# ) in product(iia_metric_list, variant_list, variant_list):

iia_variant = "average"
um_variant = "worst_case"
tiebreak = "lex"
for metric in iia_metric_list:
    plots_dir.mkdir(parents=True, exist_ok=True)

    for voting_rule in [
        "borda",
        "stv",
        "plurality",
        "2-approval",
        "3-approval",
        "ranked-pairs",
    ]:
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

        all_files = glob(
            f"{top_dir}/stats/bt_2_bloc_profile_stats/3_seats/{metric}/**/**/{iia_file_basename}.json"
        )

        iia_data = []
        um_data = []
        for i, iia_file in enumerate(all_files):
            with open(iia_file, "r") as f:
                iia_data.extend(json.load(f))
            um_file = (
                iia_file.replace("METRIC_sigma_IIA", "METRIC_sigma_UM")
                .replace("__INTERP_None", "__INTERP_asin")
                .replace("/sigma_IIA", "/sigma_UM")
                .replace(f"_VARIANT_{iia_variant}", f"_VARIANT_{um_variant}")
            )
            with open(um_file, "r") as f_um:
                um_data.extend(json.load(f_um))

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

        ax.scatter(um_data, iia_data, color=rule_color_map[voting_rule])
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
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
