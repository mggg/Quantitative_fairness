import matplotlib.pyplot as plt
import json
import seaborn as sns
import pandas as pd
from fractions import Fraction
from matplotlib.patches import Patch
from pathlib import Path
import click


def load_file(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    return []


def create_ordered_dict_for_metric_and_alpha(
    metric_base_name,
    alpha,
    ordered_rules,
    ordered_n_cands,
    stat_file_base_dir,
    n_seats,
    variant,
    tiebreak,
    interpolation_type,
):
    return {
        rule: {
            n_cands: load_file(
                str(
                    Path(
                        f"{stat_file_base_dir}/{metric_base_name}/{n_cands:02d}/alpha_{alpha:.2f}/METRIC_{metric_base_name}__SEATS_{n_seats}__NCANDS_{n_cands}__ALPHA_{alpha:.2f}__TYPE_{rule}__VARIANT_{variant}__TIEBREAK_{tiebreak}__INTERP_{interpolation_type}.json"
                    ).resolve()
                )
            )
            for n_cands in ordered_n_cands
        }
        for rule in ordered_rules
    }


def build_plot_for_metric_and_alpha(
    metric_base_name,
    alpha,
    ordered_rules,
    ordered_n_cands,
    rule_color_map,
    ax,
    y_label,
    stat_file_base_dir,
    n_seats,
    variant,
    tiebreak,
    interpolation_type,
):
    ordered_outputs = create_ordered_dict_for_metric_and_alpha(
        metric_base_name,
        alpha,
        ordered_rules,
        ordered_n_cands,
        stat_file_base_dir,
        n_seats,
        variant,
        tiebreak,
        interpolation_type,
    )

    df_list = []
    for n_cands in ordered_n_cands:
        df_data = [ordered_outputs[rule][n_cands] for rule in ordered_rules]
        df = pd.DataFrame(df_data, index=ordered_outputs.keys()).T
        df = df.melt(var_name="rule", value_name="value")
        df["n_cands"] = n_cands
        df_list.append(df)

    long = pd.concat(df_list, ignore_index=True)

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=False,
        fliersize=1,
        whis=[1, 99],
    )

    ax.set_ylabel(y_label)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(
        f"Metric: {y_label}, $\\alpha$={Fraction(alpha).limit_denominator()} Seats: {n_seats}"
    )


@click.command()
@click.option("--n-seats", type=int, default=1, help="Number of seats")
@click.option("--variant", type=click.Choice(["worst_case", "average"]))
@click.option("--tiebreak", type=click.Choice(["lex", "random"]))
def main(n_seats, variant, tiebreak):
    top_dir = str(Path(__file__).resolve().parents[2])
    stat_file_base_dir = str(
        Path(f"{top_dir}/stats/bt_profile_stats/{n_seats}_seats").resolve()
    )

    all_rules = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
    ]
    cand_counts = list(range(6, 10))
    alpha_values = [1 / 3, 1 / 2, 1, 2, 3]

    # ====================

    metric_label_pairs = [
        (
            f"sigma_UM_worst_case_asin_{tiebreak}",
            "sigma_UM",
            "worst_case",
            "asin",
            "$\\sigma_{UM}$ ranking ASIN",
        ),
        (
            f"sigma_UM_winner_set_worst_case_asin_{tiebreak}",
            "sigma_UM_winner_set",
            "worst_case",
            "asin",
            "$\\sigma_{UM}$ winner-set ranking ASIN",
        ),
        (
            f"sigma_IIA_average_{tiebreak}",
            "sigma_IIA",
            "average",
            "None",
            "$\\sigma_{IIA}$ ranking",
        ),
        (
            f"sigma_IIA_all_subset_average_{tiebreak}",
            "sigma_IIA_all_subset",
            "average",
            "None",
            "$\\sigma_{IIA}$ subset",
        ),
        (
            f"sigma_IIA_winner_set_average_{tiebreak}",
            "sigma_IIA_winner_set",
            "average",
            "None",
            "$\\sigma_{IIA}$ winner-set",
        ),
    ]
    scale = 1
    fig, ax = plt.subplots(
        len(metric_label_pairs),
        len(alpha_values),
        figsize=(7 * len(alpha_values) * scale, 5 * scale * len(metric_label_pairs)),
        dpi=300,
        gridspec_kw={"hspace": 0.3},
    )
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
    palette = sns.color_palette("colorblind", len(all_rules))
    rule_color_map = dict(zip(all_rules, palette))
    output_folder = Path(f"{top_dir}/plots/simulated_BT_plots/")
    output_folder.mkdir(parents=True, exist_ok=True)
    output_plot_name = (
        f"{output_folder}/BESTMERGE__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png"
    )

    for alpha_idx, alpha in enumerate(alpha_values):
        for idx, (
            _,
            metric_base_name,
            metric_variant,
            interpolation_type,
            y_label,
        ) in enumerate(metric_label_pairs):
            build_plot_for_metric_and_alpha(
                metric_base_name,
                alpha,
                all_rules,
                cand_counts,
                rule_color_map,
                ax[idx][alpha_idx],
                y_label=y_label,
                stat_file_base_dir=stat_file_base_dir,
                n_seats=n_seats,
                variant=metric_variant,
                tiebreak=tiebreak,
                interpolation_type=interpolation_type,
            )

    legend_patches = [Patch(facecolor=rule_color_map[r], label=r) for r in all_rules]
    fig.legend(
        handles=legend_patches,
        title="Voting Rule",
        loc="center left",
        bbox_to_anchor=(0.93, 0.5),
        frameon=True,
        fontsize="large",
        title_fontsize="large",
    )
    plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

    # ===================

    metric_label_pairs = [
        (
            f"sigma_UM_worst_case_asin_{tiebreak}",
            "sigma_UM",
            "worst_case",
            "asin",
            "$\\sigma_{UM}$ ranking ASIN",
        ),
        (
            f"sigma_UM_winner_set_worst_case_asin_{tiebreak}",
            "sigma_UM_winner_set",
            "worst_case",
            "asin",
            "$\\sigma_{UM}$ winner-set ranking ASIN",
        ),
        (
            f"sigma_IIA_average_{tiebreak}",
            "sigma_IIA",
            "worst_case",
            "None",
            "$\\sigma_{IIA}$ ranking",
        ),
        (
            f"sigma_IIA_all_subset_average_{tiebreak}",
            "sigma_IIA_all_subset",
            "average",
            "None",
            "$\\sigma_{IIA}$ subset",
        ),
        (
            f"sigma_IIA_winner_set_average_{tiebreak}",
            "sigma_IIA_winner_set",
            "average",
            "None",
            "$\\sigma_{IIA}$ winner-set",
        ),
    ]
    scale = 1
    fig, ax = plt.subplots(
        len(metric_label_pairs),
        len(alpha_values),
        figsize=(7 * len(alpha_values) * scale, 5 * scale * len(metric_label_pairs)),
        dpi=300,
        gridspec_kw={"hspace": 0.3},
    )
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
    palette = sns.color_palette("colorblind", len(all_rules))
    rule_color_map = dict(zip(all_rules, palette))
    output_folder = Path(f"{top_dir}/plots/simulated_BT_plots/")
    output_folder.mkdir(parents=True, exist_ok=True)
    output_plot_name = (
        f"{output_folder}/ALTMERGE__NSEATS_{n_seats}__TIEBREAK_{tiebreak}.png"
    )

    for alpha_idx, alpha in enumerate(alpha_values):
        for idx, (
            _,
            metric_base_name,
            metric_variant,
            interpolation_type,
            y_label,
        ) in enumerate(metric_label_pairs):
            build_plot_for_metric_and_alpha(
                metric_base_name,
                alpha,
                all_rules,
                cand_counts,
                rule_color_map,
                ax[idx][alpha_idx],
                y_label=y_label,
                stat_file_base_dir=stat_file_base_dir,
                n_seats=n_seats,
                variant=metric_variant,
                tiebreak=tiebreak,
                interpolation_type=interpolation_type,
            )

    legend_patches = [Patch(facecolor=rule_color_map[r], label=r) for r in all_rules]
    fig.legend(
        handles=legend_patches,
        title="Voting Rule",
        loc="center left",
        bbox_to_anchor=(0.93, 0.5),
        frameon=True,
        fontsize="large",
        title_fontsize="large",
    )
    plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

    # ====================

    metric_label_pairs = [
        (
            f"sigma_UM_{variant}_odds_{tiebreak}",
            "sigma_UM",
            "odds",
            "$\\sigma_{UM}$ ranking ODDS",
        ),
        (
            f"sigma_UM_{variant}_asin_{tiebreak}",
            "sigma_UM",
            "asin",
            "$\\sigma_{UM}$ ranking ASIN",
        ),
        (
            f"sigma_UM_winner_set_{variant}_odds_{tiebreak}",
            "sigma_UM_winner_set",
            "odds",
            "$\\sigma_{UM}$ winner-set ranking ODDS",
        ),
        (
            f"sigma_UM_winner_set_{variant}_asin_{tiebreak}",
            "sigma_UM_winner_set",
            "asin",
            "$\\sigma_{UM}$ winner-set ranking ASIN",
        ),
        (
            f"sigma_IIA_{variant}_{tiebreak}",
            "sigma_IIA",
            "None",
            "$\\sigma_{IIA}$ ranking",
        ),
        (
            f"sigma_IIA_all_subset_{variant}_{tiebreak}",
            "sigma_IIA_all_subset",
            "None",
            "$\\sigma_{IIA}$ subset",
        ),
        (
            f"sigma_IIA_winner_set_{variant}_{tiebreak}",
            "sigma_IIA_winner_set",
            "None",
            "$\\sigma_{IIA}$ winner-set",
        ),
    ]
    scale = 1
    fig, ax = plt.subplots(
        len(metric_label_pairs),
        len(alpha_values),
        figsize=(7 * len(alpha_values) * scale, 5 * scale * len(metric_label_pairs)),
        dpi=300,
        gridspec_kw={"hspace": 0.3},
    )
    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
    palette = sns.color_palette("colorblind", len(all_rules))
    rule_color_map = dict(zip(all_rules, palette))
    output_folder = Path(f"{top_dir}/plots/simulated_BT_plots/")
    output_folder.mkdir(parents=True, exist_ok=True)
    output_plot_name = f"{output_folder}/AGGREGATE__NSEATS_{n_seats}__VARIANT_{variant}__TIEBREAK_{tiebreak}.png"

    for alpha_idx, alpha in enumerate(alpha_values):
        for idx, (_, metric_base_name, interpolation_type, y_label) in enumerate(
            metric_label_pairs
        ):
            build_plot_for_metric_and_alpha(
                metric_base_name,
                alpha,
                all_rules,
                cand_counts,
                rule_color_map,
                ax[idx][alpha_idx],
                y_label=y_label,
                stat_file_base_dir=stat_file_base_dir,
                n_seats=n_seats,
                variant=variant,
                tiebreak=tiebreak,
                interpolation_type=interpolation_type,
            )

    legend_patches = [Patch(facecolor=rule_color_map[r], label=r) for r in all_rules]
    fig.legend(
        handles=legend_patches,
        title="Voting Rule",
        loc="center left",
        bbox_to_anchor=(0.93, 0.5),
        frameon=True,
        fontsize="large",
        title_fontsize="large",
    )
    plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)

    metric_label_pairs = [
        (
            f"sigma_UM_{variant}_odds_{tiebreak}",
            "sigma_UM",
            "odds",
            "$\\sigma_{UM}$ ranking ODDS",
        ),
        (
            f"sigma_UM_{variant}_asin_{tiebreak}",
            "sigma_UM",
            "asin",
            "$\\sigma_{UM}$ ranking ASIN",
        ),
        (
            f"sigma_UM_winner_set_{variant}_odds_{tiebreak}",
            "sigma_UM_winner_set",
            "odds",
            "$\\sigma_{UM}$ winner-set ranking ODDS",
        ),
        (
            f"sigma_UM_winner_set_{variant}_asin_{tiebreak}",
            "sigma_UM_winner_set",
            "asin",
            "$\\sigma_{UM}$ winner-set ranking ASIN",
        ),
        (
            f"sigma_IIA_{variant}_{tiebreak}",
            "sigma_IIA",
            "None",
            "$\\sigma_{IIA}$ ranking",
        ),
        (
            f"sigma_IIA_all_subset_{variant}_{tiebreak}",
            "sigma_IIA_all_subset",
            "None",
            "$\\sigma_{IIA}$ subset",
        ),
        (
            f"sigma_IIA_winner_set_{variant}_{tiebreak}",
            "sigma_IIA_winner_set",
            "None",
            "$\\sigma_{IIA}$ winner-set",
        ),
    ]
    for idx, (_, metric_base_name, interpolation_type, y_label) in enumerate(
        metric_label_pairs
    ):
        output_folder = Path(f"{top_dir}/plots/simulated_BT_plots/")
        output_folder.mkdir(parents=True, exist_ok=True)
        output_plot_name = f"{output_folder}/METRIC_{metric_base_name}__NSEATS_{n_seats}__VARIANT_{variant}__TIEBREAK_{tiebreak}__INTERP_{interpolation_type}.png"
        fig, ax = plt.subplots(
            1,
            len(alpha_values),
            figsize=(7 * len(alpha_values) * scale, 5 * scale),
            dpi=300,
            gridspec_kw={"hspace": 0.3},
        )
        sns.set_theme(
            style="whitegrid", context="notebook", font="serif", font_scale=1.2
        )
        palette = sns.color_palette("colorblind", len(all_rules))
        rule_color_map = dict(zip(all_rules, palette))
        for alpha_idx, alpha in enumerate(alpha_values):
            build_plot_for_metric_and_alpha(
                metric_base_name,
                alpha,
                all_rules,
                cand_counts,
                rule_color_map,
                ax[alpha_idx],
                y_label=y_label,
                stat_file_base_dir=stat_file_base_dir,
                n_seats=n_seats,
                variant=variant,
                tiebreak=tiebreak,
                interpolation_type=interpolation_type,
            )

        legend_patches = [
            Patch(facecolor=rule_color_map[r], label=r) for r in all_rules
        ]
        fig.legend(
            handles=legend_patches,
            title="Voting Rule",
            loc="center left",
            bbox_to_anchor=(0.93, 0.5),
            frameon=True,
            fontsize="large",
            title_fontsize="large",
        )
        plt.savefig(output_plot_name, bbox_inches="tight", dpi=300)


if __name__ == "__main__":
    main()
