import matplotlib.pyplot as plt
import json
from glob import glob
import seaborn as sns
import pandas as pd


def construct_df_scottish(data_dictionary, n_cands, metric):
    """
    Helper function to construct a DataFrame from the data dictionary.
    Included to improve readability.
    """
    df_data = []
    for _, data in data_dictionary.items():
        df_data.append(data[str(n_cands)][metric])

    return pd.DataFrame(df_data, index=data_dictionary.keys()).T


def build_plot_for_metric_scottish(metric, ax, y_label="", use_one=False):
    """
    Helper function to build a boxplot for a given metric.
    Included to improve readability.
    """
    df_list = []
    for n_cands in range(3, 15):
        df = construct_df_scottish(ordered_outputs, n_cands, metric)
        df = df.melt(var_name="rule", value_name="value")
        df["n_cands"] = n_cands
        df_list.append(df)

    if use_one:
        df_list = [df[df["rule"] == "borda"] for df in df_list]

    long = pd.concat(df_list, ignore_index=True)

    palette = sns.color_palette("colorblind", len(ordered_rules))
    rule_color_map = dict(zip(ordered_rules, palette))

    sns.boxplot(
        data=long,
        x="n_cands",
        y="value",  # σ_IIA values
        hue="rule",
        palette=rule_color_map,
        dodge=True,
        ax=ax,
        legend=not use_one,  # don't show legend if only one rule
        whis=[1, 99],  # use 1st and 99th percentiles
    )

    ax.set_ylabel(y_label)
    if not use_one:
        ax.legend(title="Voting rule", bbox_to_anchor=(1, 0.5), loc="center left")


if __name__ == "__main__":
    ordered_rules = ["borda", "3-approval", "2-approval", "plurality", "stv"]

    # ==========================
    # Make the scottish boxplots
    # ==========================
    all_output_files = glob("./scottish_stats/*output.json")

    outputs_by_type = {}
    for output_file in all_output_files:
        with open(output_file, "r") as f:
            output = json.load(f)
        election_type = output_file.split("/")[-1].split("_")[0]
        outputs_by_type[election_type] = output

    ordered_outputs = {key: outputs_by_type[key] for key in ordered_rules}

    fig, ax = plt.subplots(3, 1, figsize=(20, 18))

    sns.set_theme(style="whitegrid", context="notebook", font="serif", font_scale=1.2)
    build_plot_for_metric_scottish(
        "n_voters", ax[0], y_label="Number of voters", use_one=True
    )
    build_plot_for_metric_scottish("sigma_IIA", ax[1], y_label="$\sigma_{IIA}$")
    build_plot_for_metric_scottish("sigma_UM", ax[2], y_label="$\sigma_{UM}$")
    plt.savefig("./plots/scottish_sigma_plots.png", bbox_inches="tight", dpi=300)

    # ===========================
    # Make the scottish stats csv
    # ===========================
    all_stats_files = glob("./scottish_stats/*stats.json")

    stats_by_type = {}
    for stats_file in all_stats_files:
        with open(stats_file, "r") as f:
            stats = json.load(f)
        election_type = stats_file.split("/")[-1].split("_")[0]
        stats_by_type[election_type] = stats
    df = pd.concat(
        {rule: pd.DataFrame(sub).T for rule, sub in stats_by_type.items()},
        names=["rule", "n_cands"],  # names for the new index levels
    )

    df.index = df.index.set_levels(df.index.levels[1].astype(int), level="n_cands")

    df = df.reindex(
        pd.MultiIndex.from_product(
            [ordered_rules, range(3, 15)], names=["rule", "n_cands"]
        ),
    )

    df.to_csv("./scottish_stats/scottish_stats_all.csv")
