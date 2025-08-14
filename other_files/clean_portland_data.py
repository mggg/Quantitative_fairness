from votekit.cvr_loaders import load_csv
from votekit.cleaning import remove_and_condense, remove_repeated_candidates
from pathlib import Path


if __name__ == "__main__":
    top_dir = str(Path(__file__).resolve().parents[1])

    for district in ["D1", "D2", "D3", "D4"]:
        url = f"https://raw.githubusercontent.com/mggg/Portland-Postmortem/refs/heads/main/Restructured%20Repo/CVRs/raw_votekit_csv/Portland_{district}_raw_votekit_format.csv"
        raw_profile = load_csv(url, rank_cols=[1, 2, 3, 4, 5, 6])
        raw_profile = remove_repeated_candidates(raw_profile)

        clean_profile = remove_and_condense(
            ["Uncertified Write In", "overvote"]
            + [f"Write-in-{i}" for i in range(120, 132)],
            raw_profile,
        )

        # Save the cleaned profile
        clean_profile.to_csv(f"{top_dir}/data/Portland_{district}_cleaned_votekit.csv")
