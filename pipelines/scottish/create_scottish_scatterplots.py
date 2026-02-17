"""Create scatter plots comparing UM and IIA metrics in Scottish data."""

from glob import glob
from itertools import product
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import pandas as pd
import seaborn as sns


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
    "3-approval": "3-Approval",
    "2-approval": "2-Approval",
    "plurality": "Plurality",
    "stv": "STV",
    "ranked-pairs": "Ranked Pairs",
    "random": "Random",
}


def construct_df_scottish(
    data_dictionary: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    n_cands: int,
    metric: str,
) -> pd.DataFrame:
    """Construct a DataFrame for a metric at a fixed candidate count.

    Args:
        data_dictionary (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested mapping of rule to candidate count to metric values.
        n_cands (int): Number of candidates to extract.
        metric (str): Metric key to select.

    Returns:
        pd.DataFrame: A transposed DataFrame with rules as columns.
    """
    df_data = []
    for _, data in data_dictionary.items():
        df_data.append(data[str(n_cands)][metric])

    return pd.DataFrame(df_data, index=data_dictionary.keys()).T  # ty: ignore


def build_plot_for_metric_scottish(
    metric: str,
    ordered_outputs: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    ordered_rules: Sequence[str],
    n_cand_list: Sequence[int],
    ax: Axes,
    y_label: str = "",
    use_one: bool = False,
) -> None:
    """Build a boxplot for a single metric across candidate counts.

    Args:
        metric (str): Metric key to plot.
        ordered_outputs (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested mapping of rule to candidate count to metric values.
        ordered_rules (Sequence[str]): Ordered list of rules (for stable plotting).
        n_cand_list (Sequence[int]): Candidate counts to include.
        ax (Axes): Matplotlib axes to draw into.
        y_label (str): Label for the y-axis.
        use_one (bool): Whether to plot only the Borda rule.
    """
    df_list = []
    for n_cands in n_cand_list:
        df = construct_df_scottish(ordered_outputs, n_cands, metric)
        df = df.melt(var_name="rule", value_name="value")
        df["n_cands"] = n_cands
        df_list.append(df)

    if use_one:
        df_list = [df[df["rule"] == "borda"] for df in df_list]

    long = pd.concat(df_list, ignore_index=True)

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",  # σ_IIA values
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=not use_one,  # don't show legend if only one rule
        whis=[1, 99],  # use 1st and 99th percentiles # ty: ignore
    )

    ax.set_ylabel(y_label, fontsize=16)
    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


def load_outputs_by_election_type(
    stats_dir: Path,
    ordered_rules: Sequence[str],
) -> dict[str, dict[str, dict[str, list[float]]]]:
    """Load Scottish metric outputs grouped by rule and candidate size.

    Args:
        stats_dir (Path): Base directory containing Scottish metric JSON outputs.
        ordered_rules (Sequence[str]): Rules to include.

    Returns:
        dict[str, dict[str, dict[str, list[float]]]]: Nested mapping:
            ``rule -> candidate_count -> metric_key -> metric_values``.
    """
    election_type_to_metric_to_cand_count: dict[
        str, dict[str, dict[str, list[float]]]
    ] = {}

    for variant, tiebreak, voting_rule in product(
        ["average", "worst_case"], ["lex", "random"], ordered_rules
    ):
        all_output_files = glob(
            str(stats_dir / f"*{variant}*" / voting_rule / f"*{tiebreak}_output.json")
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

    outputs_by_election_type: dict[str, dict[str, dict[str, list[float]]]] = {}
    for (
        election_type,
        metric_to_cand_count,
    ) in election_type_to_metric_to_cand_count.items():
        if election_type not in outputs_by_election_type:
            outputs_by_election_type[election_type] = {}
        for metric, cand_count_to_values in metric_to_cand_count.items():
            for n_cands, value_list in cand_count_to_values.items():
                if n_cands not in outputs_by_election_type[election_type]:
                    outputs_by_election_type[election_type][n_cands] = {}
                outputs_by_election_type[election_type][n_cands][metric] = value_list

    return outputs_by_election_type


def get_limited_metric_key_pairs(
    variant_um: str = "worst_case",
    variant_iia: str = "average",
    tiebreak: str = "lex",
) -> list[tuple[str, str]]:
    """Build limited scatter metric pairs.

    Args:
        variant_um (str): UM metric variant.
        variant_iia (str): IIA metric variant.
        tiebreak (str): Tiebreak suffix used in metric keys.

    Returns:
        list[tuple[str, str]]: ``(um_metric_key, iia_metric_key)`` pairs.
    """
    return [
        (
            f"sigma_UM_{variant_um}_asin_{tiebreak}",
            f"sigma_IIA_{variant_iia}_{tiebreak}",
        ),
        (
            f"sigma_UM_winner_set_{variant_um}_asin_{tiebreak}",
            f"sigma_IIA_winner_set_{variant_iia}_{tiebreak}",
        ),
    ]


def collect_scatter_points(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    voting_rule: str,
    um_key: str,
    iia_key: str,
) -> tuple[list[float], list[float]]:
    """Collect x/y values for one rule and one UM-vs-IIA metric pair.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        voting_rule (str): Rule to extract.
        um_key (str): Metric key for x-axis values.
        iia_key (str): Metric key for y-axis values.

    Returns:
        tuple[list[float], list[float]]: ``(x_values, y_values)``.
    """
    x_data: list[float] = []
    y_data: list[float] = []

    for _, data in outputs_by_election_type[voting_rule].items():
        x_data.extend(data[um_key])
        y_data.extend(data[iia_key])

    return x_data, y_data


def draw_limited_scatter_base(
    ax: Axes, x_data: list[float], y_data: list[float], color: str
) -> None:
    """Draw the baseline limited scatter styling.

    Args:
        ax (Axes): Axes to draw on.
        x_data (list[float]): X values.
        y_data (list[float]): Y values.
        color (str): Point color.
    """
    ax.scatter(x_data, y_data, color=color)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.vlines(
        0.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
    )
    ax.vlines(
        1.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
    )
    ax.hlines(
        0.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
    )
    ax.hlines(
        1.0, -0.05, 1.05, color="grey", linestyle="-", linewidth=1, zorder=-1, alpha=0.5
    )


def build_limited_scatter_plot_name(
    scatter_dir: Path,
    voting_rule: str,
    um_key: str,
    iia_key: str,
    variant_um: str,
    variant_iia: str,
    tiebreak: str,
) -> Path:
    """Build output filename for one limited scatter plot.

    Args:
        scatter_dir (Path): Output plot directory.
        voting_rule (str): Rule name.
        um_key (str): UM metric key.
        iia_key (str): IIA metric key.
        variant_um (str): UM variant string used in key suffix.
        variant_iia (str): IIA variant string used in key suffix.
        tiebreak (str): Tiebreak string used in key suffix.

    Returns:
        Path: Full output file path.
    """
    return scatter_dir / (
        f"{voting_rule}_"
        f"{um_key.removesuffix(f'_{variant_um}_asin_{tiebreak}')}_vs_"
        f"{iia_key.removesuffix(f'_{variant_iia}_{tiebreak}')}_scatter.png"
    )


def create_limited_scatter_plot(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    voting_rule: str,
    um_key: str,
    iia_key: str,
    output_path: Path,
    overlay_fn: (
        Callable[[Axes, str, str, str, list[float], list[float]], None] | None
    ) = None,
) -> None:
    """Create and save one limited scatter plot.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        voting_rule (str): Rule to plot.
        um_key (str): X-axis metric key.
        iia_key (str): Y-axis metric key.
        output_path (Path): Output image path.
        overlay_fn (Callable[[Axes, str, str, str, list[float], list[float]], None] | None):
            Optional overlay callback receiving
            ``(ax, voting_rule, um_key, iia_key, x_data, y_data)``.
    """
    sns.set_theme(style="ticks", context="notebook", font="serif", font_scale=1.2)
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    x_data, y_data = collect_scatter_points(
        outputs_by_election_type=outputs_by_election_type,
        voting_rule=voting_rule,
        um_key=um_key,
        iia_key=iia_key,
    )
    draw_limited_scatter_base(
        ax=ax, x_data=x_data, y_data=y_data, color=rule_color_map[voting_rule]
    )
    if overlay_fn is not None:
        overlay_fn(ax, voting_rule, um_key, iia_key, x_data, y_data)
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close(fig)


def create_full_scatter_plot(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    voting_rule: str,
    um_key: str,
    iia_key: str,
    um_label: str,
    iia_label: str,
    output_path: Path,
    plot_title: str,
) -> None:
    """Create and save one full-style scatter plot (legacy reference style).

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        voting_rule (str): Rule to plot.
        um_key (str): X-axis metric key.
        iia_key (str): Y-axis metric key.
        um_label (str): X-axis label.
        iia_label (str): Y-axis label.
        output_path (Path): Output image path.
        plot_title (str): Plot title text.
    """
    sns.set_theme(style="ticks", context="notebook", font="serif", font_scale=1.2)
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    x_data, y_data = collect_scatter_points(
        outputs_by_election_type=outputs_by_election_type,
        voting_rule=voting_rule,
        um_key=um_key,
        iia_key=iia_key,
    )
    ax.scatter(x_data, y_data, color=rule_color_map[voting_rule])
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(plot_title, fontsize=20)
    ax.set_xlabel(um_label, fontsize=16)
    ax.set_ylabel(iia_label, fontsize=16)
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close(fig)


def run_full_scatter_plots(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    ordered_rules: Sequence[str],
    output_dir: Path,
) -> None:
    """Legacy exhaustive scatter workflow kept for reference.

    This mirrors the previously commented-out section that swept variants and
    tiebreaks for both ranking and winner-set metric families.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        ordered_rules (Sequence[str]): Rules to include.
        output_dir (Path): Base plot output directory.
    """
    for variant1, variant2, tiebreak in product(
        ["average", "worst_case"], ["average", "worst_case"], ["lex", "random"]
    ):
        um_ranking = [
            (f"sigma_UM_{variant1}_odds_{tiebreak}", "$\\sigma_{UM}$ ranking ODDS"),
            (f"sigma_UM_{variant1}_asin_{tiebreak}", "$\\sigma_{UM}$ ranking ASIN"),
        ]

        um_winner_set = [
            (
                f"sigma_UM_winner_set_{variant1}_odds_{tiebreak}",
                "$\\sigma_{UM}$ winner-set ODDS",
            ),
            (
                f"sigma_UM_winner_set_{variant1}_asin_{tiebreak}",
                "$\\sigma_{UM}$ winner-set ASIN",
            ),
        ]

        iia_ranking = [
            (f"sigma_IIA_{variant2}_{tiebreak}", "$\\sigma_{IIA}$ ranking single"),
            (
                f"sigma_IIA_all_subset_{variant2}_{tiebreak}",
                "$\\sigma_{IIA}$ ranking all subset",
            ),
        ]

        iia_winner_set = [
            (
                f"sigma_IIA_winner_set_{variant2}_{tiebreak}",
                "$\\sigma_{IIA}$ winner-set single",
            ),
            (
                f"sigma_IIA_winner_set_all_subset_{variant2}_{tiebreak}",
                "$\\sigma_{IIA}$ winner-set all subset",
            ),
        ]

        for voting_rule in ordered_rules:
            for (um_key, um_label), (iia_key, iia_label) in product(
                um_ranking, iia_ranking
            ):
                scatter_dir = output_dir / "scatter" / f"um-{variant1}_iia-{variant2}"
                scatter_dir.mkdir(parents=True, exist_ok=True)
                plot_name = (
                    scatter_dir / f"{voting_rule}_{um_key}_vs_{iia_key}_scatter.png"
                )
                create_full_scatter_plot(
                    outputs_by_election_type=outputs_by_election_type,
                    voting_rule=voting_rule,
                    um_key=um_key,
                    iia_key=iia_key,
                    um_label=um_label,
                    iia_label=iia_label,
                    output_path=plot_name,
                    plot_title=voting_rule,
                )

            for (um_key, um_label), (iia_key, iia_label) in product(
                um_winner_set, iia_winner_set
            ):
                scatter_dir = (
                    output_dir / "scatter" / f"umws-{variant1}_iiaws-{variant2}"
                )
                scatter_dir.mkdir(parents=True, exist_ok=True)
                plot_name = (
                    scatter_dir / f"{voting_rule}_{um_key}_vs_{iia_key}_scatter.png"
                )
                create_full_scatter_plot(
                    outputs_by_election_type=outputs_by_election_type,
                    voting_rule=voting_rule,
                    um_key=um_key,
                    iia_key=iia_key,
                    um_label=um_label,
                    iia_label=iia_label,
                    output_path=plot_name,
                    plot_title=titles[voting_rule],
                )


def run_limited_scatter_plots(
    outputs_by_election_type: Mapping[str, Mapping[str, Mapping[str, list[float]]]],
    ordered_rules: Sequence[str],
    output_dir: Path,
    variant_um: str = "worst_case",
    variant_iia: str = "average",
    tiebreak: str = "lex",
    scatter_subdir: str = "scatter_by_voting_rule",
    overlay_fn: (
        Callable[[Axes, str, str, str, list[float], list[float]], None] | None
    ) = None,
) -> None:
    """Generate the limited Scottish scatter plots for all rules.

    Args:
        outputs_by_election_type (Mapping[str, Mapping[str, Mapping[str, list[float]]]]):
            Nested metric values by rule and candidate count.
        ordered_rules (Sequence[str]): Rules to include.
        output_dir (Path): Base plot output directory.
        variant_um (str): UM metric variant.
        variant_iia (str): IIA metric variant.
        tiebreak (str): Tiebreak suffix used in metric keys.
        scatter_subdir (str): Subdirectory name under ``output_dir``.
        overlay_fn (Callable[[Axes, str, str, str, list[float], list[float]], None] | None):
            Optional overlay callback for each plot.
    """
    scatter_dir = output_dir / scatter_subdir
    scatter_dir.mkdir(parents=True, exist_ok=True)
    metric_pairs = get_limited_metric_key_pairs(
        variant_um=variant_um,
        variant_iia=variant_iia,
        tiebreak=tiebreak,
    )

    for voting_rule in ordered_rules:
        for um_key, iia_key in metric_pairs:
            plot_name = build_limited_scatter_plot_name(
                scatter_dir=scatter_dir,
                voting_rule=voting_rule,
                um_key=um_key,
                iia_key=iia_key,
                variant_um=variant_um,
                variant_iia=variant_iia,
                tiebreak=tiebreak,
            )
            create_limited_scatter_plot(
                outputs_by_election_type=outputs_by_election_type,
                voting_rule=voting_rule,
                um_key=um_key,
                iia_key=iia_key,
                output_path=plot_name,
                overlay_fn=overlay_fn,
            )


def main() -> None:
    """Run the Scottish limited scatterplot pipeline."""
    ordered_rules = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
        "random",
    ]
    top_dir = Path(__file__).resolve().parents[2]
    stats_dir = top_dir / "stats" / "scottish_stats"
    output_dir = top_dir / "plots" / "scottish"
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs_by_election_type = load_outputs_by_election_type(
        stats_dir=stats_dir,
        ordered_rules=ordered_rules,
    )
    run_limited_scatter_plots(
        outputs_by_election_type=outputs_by_election_type,
        ordered_rules=ordered_rules,
        output_dir=output_dir,
    )

    # Old exhaustive section kept for reference.
    # run_full_scatter_plots(
    #     outputs_by_election_type=outputs_by_election_type,
    #     ordered_rules=ordered_rules,
    #     output_dir=output_dir,
    # )


if __name__ == "__main__":
    main()
