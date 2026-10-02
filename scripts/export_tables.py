"""Export the NY and Portland statistics as one row per election and voting rule."""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voting_metrics_main_code.replication import ROOT


def main(dataset: str, stats_root: Path | None = None, output_root: Path = ROOT) -> None:
    """Export one dataset's scores to a table beneath the selected run root.

    Args:
        dataset (str): Dataset token, 'ny' or 'portland'.
        stats_root (Path | None, optional): Parent of the dataset statistics directories. None uses
            the selected run root's stats directory. Defaults to None.
        output_root (Path, optional): Run root containing the exported tables. Defaults to ROOT.

    Raises:
        FileNotFoundError: No election statistics are available for the requested dataset.
        json.JSONDecodeError: A statistics file is not valid JSON.
        OSError: An input cannot be read or the table cannot be written.
    """
    output_root = output_root.resolve()
    stats_root = (stats_root or output_root / "stats").resolve()
    print(f"Statistics: {stats_root}; output root: {output_root}")

    rows = []
    for path in sorted((stats_root / f"{dataset}_stats").glob("*_output.json")):
        data = json.loads(path.read_text())
        elections = {"NY Mayor": data} if dataset == "ny" else data

        for election, metrics in elections.items():
            rows.append(
                {
                    "election": election,
                    "rule": path.stem.removesuffix("_output"),
                    **{metric: values[0] for metric, values in metrics.items()},
                }
            )

    if not rows:
        raise FileNotFoundError(
            f"No election statistics found in {stats_root / (dataset + '_stats')}"
        )

    output_dir = output_root / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / f"{dataset}.csv").open("w", newline="") as table_file:
        writer = csv.DictWriter(table_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("ny", "portland"))
    parser.add_argument("--stats-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    main(args.dataset, args.stats_dir, args.output_dir.resolve())
