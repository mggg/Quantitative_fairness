"""Create limited Scottish CSV exports for selected metrics."""

import argparse
import json
import sys
from glob import escape, glob
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from voting_metrics_main_code.constants import RULE_ORDER
from voting_metrics_main_code.replication import ROOT


def main(*, stats_root: Path | None = None, output_root: Path = ROOT) -> None:
    """Export primary Scottish metrics to one election-level CSV per voting rule.

    Args:
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()
    print(f"Statistics: {stats_root}")
    print(f"Output root: {output_root}")

    (output_root / "stats" / "scottish_stats").mkdir(parents=True, exist_ok=True)

    for voting_rule in RULE_ORDER:
        all_files = glob(f"{escape(str(stats_root))}/scottish_stats/**/{voting_rule}/*.json")

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
            str(output_root / "stats" / "scottish_stats" / f"scottish_{voting_rule}_limited.csv"),
            index=False,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(stats_root=args.stats_dir, output_root=args.output_dir)
