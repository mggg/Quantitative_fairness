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


DEFAULT_FONT_SIZE = 24
ALT_FONT_SIZES = {
    "random": 16,
    "ranked-pairs": 16,
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

    cache_dir = TOP_DIR / ".waterfall_cache" / "bt_proportionality"
    cache_dir.mkdir(parents=True, exist_ok=True)

    N_SEATS = 3
    for election_type in AllowedRule:
        rule_df = df.query("method == @election_type")
        _, ax = plt.subplots(1, 1, figsize=(8, 8))

        cache_file = cache_dir / f"{election_type}_waterfall_cache.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
            all_x_values = cached_data["all_x_values"]
            all_y_values = cached_data["all_y_values"]
        else:
            all_x_values = []
            all_y_values = []
            for pat in tqdm(all_settings_strings):
                filtered = rule_df[rule_df["file"].str.contains(pat, regex=False, na=False)]
                all_x_values.append(
                    float(filtered["expected_proportion"].iloc[0])
                )  # They are all the same for a given setting
                all_y_values.append(float(filtered["observed_proportion"].values.mean()))
            with open(cache_file, "w") as f:
                json.dump({"all_x_values": all_x_values, "all_y_values": all_y_values}, f)

        points = list(zip(all_x_values, all_y_values))

        ax.plot(
            all_x_values,
            all_y_values,
            color=rule_color_map[election_type],
            marker="o",
            linestyle="None",
        )

        boxes = [(i / N_SEATS, (i + 1) / N_SEATS) for i in range(N_SEATS + 1)]

        def is_point_in_box(point, box):
            # Needed to deal with floating point precision issues when checking if a point is in a box
            eps = 1e-12
            return (
                box[0] - eps <= point[0] <= box[1] + eps
                and box[0] - eps <= point[1] <= box[1] + eps
            )

        points_in_boxes = sum(
            1 for point in points if any(is_point_in_box(point, box) for box in boxes)
        )

        election_type_str = f"Election type: {election_type:>12}"
        points_in_boxes_str = f"Points in boxes: {points_in_boxes} / {len(points)}"
        print(f"{election_type_str:<20}, {points_in_boxes_str:<50}")

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

        ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

        ax.set_xlim(min(ticks) - 0.01, max(ticks) + 0.01)
        ax.set_ylim(min(ticks) - 0.01, max(ticks) + 0.01)

        ax.set_xticks(
            ticks,
            labels=[f"{tick:.1f}" for tick in ticks],
            fontsize=ALT_FONT_SIZES.get(election_type, DEFAULT_FONT_SIZE),
        )
        ax.set_yticks(
            ticks,
            labels=[f"{tick:.1f}" for tick in ticks],
            fontsize=ALT_FONT_SIZES.get(election_type, DEFAULT_FONT_SIZE),
        )

        ax.set_aspect("equal", adjustable="box")
        # print(f"Saving {election_type} waterfall plot...")
        plt.savefig(
            f"{TOP_DIR}/plots/bt_plots/waterfall/{election_type}_waterfall.png",
            dpi=300,
            bbox_inches="tight",
        )


if __name__ == "__main__":
    main()
