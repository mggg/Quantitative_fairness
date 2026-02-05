"""This script generates waterfall plots for the Bradley-Terry proportionality analysis."""

import json
import pandas as pd
from glob import glob
import matplotlib.pyplot as plt
import numpy as np
from tqdm.auto import tqdm
from itertools import product
from pathlib import Path

TOP_DIR = Path(__file__).parents[3]

rule_color_map = {
    "borda": "#1460bc",  # lightblue
    "3-approval": "#8cb500",  # applegreen
    "2-approval": "#218c21",  # forestgreen
    "plurality": "#d11942",  # alizarin
    "stv": "#ffc40c",  # mikadoyellow
    "ranked-pairs": "#ffb7c4",  # cherryblossompink
    "random": "#707f8e",  # slategray
}

AllowedRule = (
    "borda",
    "3-approval",
    "2-approval",
    "plurality",
    "stv",
    "ranked-pairs",
    "random",
)


def main():
    n_samples = 100

    b_bloc_proportions = [0.5, 0.6, 0.7, 0.8, 0.9]
    alpha_combinations = [
        (1, 1, 1, 1),
        (0.5, 0.5, 0.5, 0.5),
        (2, 2, 2, 2),
        (1, 0.5, 1, 0.5),
        (1, 2, 1, 2),
        (0.5, 1, 0.5, 1),
        (2, 1, 2, 1),
    ]
    cohesion_combinations = [
        (0.7, 0.7),
        (0.7, 0.9),
        (0.9, 0.7),
        (0.9, 0.9),
    ]
    candidate_count_combinations = [
        (2, 6),
        (4, 4),
        (6, 2),
        (2, 8),
        (5, 5),
        (8, 2),
    ]

    all_settings_strings = dict()
    for (n_a_cands, n_b_cands), b_bloc_proportion, (a_coh, b_coh), (
        aa_al,
        ab_al,
        ba_al,
        bb_al,
    ), i in product(
        candidate_count_combinations,
        b_bloc_proportions,
        cohesion_combinations,
        alpha_combinations,
        list(range(n_samples)),
    ):
        settings_str = (
            f"{n_a_cands:02d}_{n_b_cands:02d}/"
            f"b_proportion_{b_bloc_proportion}"
            f"__ALPHA_({aa_al:.2f},{ab_al:.2f},{ba_al:.2f},{bb_al:.2f})"
            f"__COHESION_({a_coh:.2f},{b_coh:.2f})"
        )
        all_settings_strings[settings_str] = True

    list(all_settings_strings.keys())[0]

    all_files = glob(f"{TOP_DIR}/stats/bt_proportionality/*.json")
    df_list = []
    for path in all_files:
        with open(path, "r") as f:
            data = json.load(f)

        rows = []
        for file_path, methods in data.items():
            for method, vals in methods.items():
                rows.append(
                    {
                        "file": file_path,
                        "method": method,
                        "expected_proportion": vals.get("expected_proportion"),
                        "observed_proportion": vals.get("observed_proportion"),
                    }
                )

        df_list.append(pd.DataFrame(rows))

    df = pd.concat(df_list, ignore_index=True)
    df["file"] = df["file"].str.split("/data/").str[1]

    N_SEATS = 3
    for election_type in AllowedRule:
        rule_df = df.query("method == @election_type")
        _, ax = plt.subplots()

        all_x_values = []
        all_y_values = []
        for pat in tqdm(all_settings_strings):
            filtered = rule_df[rule_df["file"].str.contains(pat, regex=False, na=False)]
            all_x_values.append(
                float(filtered["expected_proportion"].iloc[0])
            )  # They are all the same for a given setting
            all_y_values.append(float(filtered["observed_proportion"].values.mean()))

        ax.plot(
            all_x_values,
            all_y_values,
            color=rule_color_map[election_type],
            marker="o",
            linestyle="None",
        )
        ax.step(
            np.linspace(0, 1, N_SEATS + 1),
            np.arange(0, 1.1, 1 / N_SEATS),
            linestyle="dashed",
            c="gray",
            where="pre",
        )
        ax.step(
            np.linspace(0, 1, N_SEATS + 1),
            np.arange(0, 1.1, 1 / N_SEATS),
            linestyle="dashed",
            c="gray",
            where="post",
        )
        ax.set_xlim(-0.01, 1.01)
        ax.set_ylim(-0.01, 1.01)
        ax.set_aspect("equal", adjustable="box")
        print(f"Saving {election_type} waterfall plot...")
        plt.savefig(
            f"{TOP_DIR}/plots/bt_plots/waterfall/{election_type}_waterfall.png",
            dpi=300,
            bbox_inches="tight",
        )


if __name__ == "__main__":
    main()
