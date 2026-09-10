"""Collect Portland election statistics across rules and metrics."""

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, cast

from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_winner_set,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import (
    AllowedRule,
    build_voting_rule,
)


def score_profile(
    profile: RankProfile,
    election_name: AllowedRule,
    metric_functions: dict[str, Callable[..., float]],
    district: str,
    *,
    seed: int = 0,
) -> dict[str, list[float]]:
    """Compute the four primary metrics for one profile with independent metric seeds.

    Args:
        seed (int, optional): Base seed for independent task streams. Defaults to 0.
        profile (RankProfile): Cleaned election profile.
        election_name (AllowedRule): Voting rule to evaluate.
        metric_functions (dict[str, Callable[..., float]]): Metrics in evaluation order.
        district (str): District token included in the random seed.

    Returns:
        dict[str, list[float]]: Voter count and metric scores as singleton lists for JSON export.
    """
    voting_rule = build_voting_rule(len(profile.candidates), election_name)
    statistics = {
        "n_voters": [int(profile.df["Weight"].sum())],
        "sigma_UM": [],
        "sigma_IIA": [],
        "sigma_UM_winner_set": [],
        "sigma_IIA_winner_set": [],
    }

    for metric_name, metric_function in metric_functions.items():
        seed_task("portland", district, election_name, metric_name, seed=seed)
        score = float(metric_function(profile, voting_rule, n_seats=3))

        statistics[metric_name].append(score)

    return statistics


def main(*, data_root: Path = ROOT / "data", output_root: Path = ROOT, seed: int = 0) -> None:
    """Save four primary metric scores for each Portland district and voting rule.

    Args:
        data_root (Path, optional): Directory containing election inputs. Defaults to ROOT / "data".
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        seed (int, optional): Base seed for independent task streams. Defaults to 0.
    """
    output_root = output_root.resolve()
    data_root = data_root.resolve()
    print(f"Data: {data_root}")
    print(f"Output root: {output_root}")
    print(f"Seed: {seed}")

    output_folder = (output_root / "stats/portland_stats").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    districts = ["D1", "D2", "D3", "D4"]
    metric_function_dict: dict[str, Callable[..., float]] = {
        "sigma_IIA": sigma_IIA,
        "sigma_UM": sigma_UM,
        "sigma_IIA_winner_set": sigma_IIA_winner_set,
        "sigma_UM_winner_set": sigma_UM_winner_set,
    }
    all_election_types: list[AllowedRule] = [
        "borda",
        "3-approval",
        "2-approval",
        "plurality",
        "stv",
        "ranked-pairs",
    ]

    for election_name in all_election_types:
        output_file = Path(output_folder_base) / f"{election_name}_output.json"

        if output_file.exists() or output_file.is_symlink():
            print(f"Skipping existing result: {output_file}. Move it manually to recompute.")
            continue

        portland_election_stats = {}

        for district in districts:
            print(f"Processing {election_name} for {district}")
            profile = RankProfile.from_csv(data_root / f"Portland_{district}_cleaned_votekit.csv")
            statistics = score_profile(
                cast(RankProfile, profile), election_name, metric_function_dict, district, seed=seed
            )

            portland_election_stats[district] = statistics

        with new_data_file(Path(output_file)) as temporary, temporary.open("w") as f:
            json.dump(portland_election_stats, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    main(data_root=args.data_dir, output_root=args.output_dir, seed=args.seed)
