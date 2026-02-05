"""Create limited Scottish CSV exports for selected metrics."""

from glob import glob
from pathlib import Path
import pandas as pd
import json

script_dir = Path(__file__).parent
top_dir = script_dir.parents[1]

for voting_rule in [
    "borda",
    "3-approval",
    "2-approval",
    "plurality",
    "stv",
    "ranked-pairs",
]:
    all_files = glob(
        str(top_dir / "stats" / "scottish_stats" / "**" / f"{voting_rule}" / "*.json")
    )

    filter_tiebreak = "lex"
    filter_metrics = [
        "sigma_UM_worst_case_asin",
        "sigma_UM_winner_set_worst_case_asin",
        "sigma_IIA_average",
        "sigma_IIA_winner_set_average",
    ]

    filtered_files = list(
        filter(
            lambda f: any(m in f for m in filter_metrics) and filter_tiebreak in f,
            all_files,
        )
    )

    df_list = []
    for f in filtered_files[:]:
        metric = Path(f).parents[1].name

        with open(f, "r") as infile:
            data = json.load(infile)

        inner_df_list = []
        for n_cands, value_dict in data.items():
            value_series = pd.Series(value_dict)
            inner_df = pd.DataFrame()
            inner_df[metric] = value_series
            inner_df["n_cands"] = int(n_cands)
            inner_df = inner_df[["n_cands", metric]]
            inner_df_list.append(inner_df)

        df = pd.concat(inner_df_list, axis=0).sort_values("n_cands")
        df_list.append(df)

    full_df = pd.concat(df_list, axis=1)
    full_df = full_df.loc[:, ~full_df.columns.duplicated()]
    full_df.index.name = "election_name"
    full_df.reset_index(inplace=True)

    full_df.to_csv(
        str(
            top_dir / "stats" / "scottish_stats" / f"scottish_{voting_rule}_limited.csv"
        ),
        index=False,
    )
