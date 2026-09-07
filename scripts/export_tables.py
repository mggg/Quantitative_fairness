"""Export the NY and Portland statistics as one row per election and voting rule."""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voting_metrics_main_code.replication import RESULTS_DIR, STATS_INPUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ny", "portland"))
    args = parser.parse_args()
    rows = []
    for path in sorted((STATS_INPUT / f"{args.dataset}_stats").glob("*_output.json")):
        data = json.loads(path.read_text())
        elections = {"NY Mayor": data} if args.dataset == "ny" else data
        for election, metrics in elections.items():
            rows.append(
                {
                    "election": election,
                    "rule": path.stem.removesuffix("_output"),
                    **{metric: values[0] for metric, values in metrics.items()},
                }
            )
    if not rows:
        parser.error("No election statistics found")
    output = RESULTS_DIR / "tables"
    output.mkdir(parents=True, exist_ok=True)
    with (output / f"{args.dataset}.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
