from glob import glob
import pandas as pd
from joblib import Parallel, delayed
from joblib_progress import joblib_progress
import numpy as np
import warnings
from votekit.cvr_loaders import load_csv
from votekit.cleaning import (
    remove_and_condense,
    remove_repeated_candidates,
    clean_profile,
)
from votekit.ballot import Ballot
from pathlib import Path


def read_subset(path: str) -> pd.DataFrame:
    warnings.filterwarnings("ignore")
    choice_column = [
        "DEM Mayor Choice 1 of 5 Citywide (026916)",
        "DEM Mayor Choice 2 of 5 Citywide (226916)",
        "DEM Mayor Choice 3 of 5 Citywide (326916)",
        "DEM Mayor Choice 4 of 5 Citywide (426916)",
        "DEM Mayor Choice 5 of 5 Citywide (526916)",
    ]
    return pd.read_excel(
        path,
        usecols=choice_column,
        engine="openpyxl",
        # dtype="string",  # optional: faster + consistent text
    )


def truncate_past_overvote(ballot: Ballot) -> Ballot:
    """
    Truncates a ballot past the first appearance of an overvote.

    Args:
        ballot (Ballot): Ballot

    Returns:
        Ballot: Ballot truncated.
    """
    new_ranking = []

    for c_set in ballot.ranking:
        if c_set == frozenset({"overvote"}):
            break
        new_ranking.append(c_set)

    return Ballot(ranking=new_ranking, weight=ballot.weight)


if __name__ == "__main__":
    top_dir = str(Path(__file__).resolve().parents[1])
    output_folder = Path(f"{top_dir}/data").resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    output_folder_base = str(output_folder)

    all_files = [p for p in glob(f"{top_dir}/data/NY_primary_data/2025*V1*.xlsx")]
    # Use threads in notebooks; adjust n_jobs as you wish
    with joblib_progress(total=len(all_files), description="Reading files"):
        dfs = Parallel(n_jobs=-1)(delayed(read_subset)(p) for p in all_files)

    df_NY = pd.concat([d for d in dfs if d is not None], ignore_index=True, copy=False)

    df_candidate_ID = pd.read_excel(
        f"{top_dir}/data/NY_primary_data/Primary Election 2025 - 06-24-2025_CandidacyID_To_Name.xlsx"
    )
    df_candidate_ID["CandidacyID"] = df_candidate_ID["CandidacyID"].astype(str)
    df_candidate_ID.set_index("CandidacyID", inplace=True)
    candidate_dict = df_candidate_ID["DefaultBallotName"].to_dict()

    all_cands = list(
        map(
            str,
            np.unique(
                df_NY[
                    [
                        f"DEM Mayor Choice {i} of 5 Citywide ({i-1 if i == 1 else i}26916)"
                        for i in range(1, 5)
                    ]
                ]
                .to_numpy()
                .astype(str)
            ),
        )
    )
    all_cands

    filtered_candidate_dict = {
        k: candidate_dict[k] for k in all_cands if k in candidate_dict
    }

    for col in df_NY.columns:
        df_NY[col] = df_NY[col].astype(str).str.strip()

    df_NY.replace(filtered_candidate_dict, inplace=True)
    df_NY.to_csv(f"{output_folder_base}/NY_mayor_all.csv", index=False)

    profile = load_csv(f"{output_folder_base}/NY_mayor_all.csv")
    profile = clean_profile(profile, truncate_past_overvote)
    profile = remove_repeated_candidates(profile)
    clean_profile = remove_and_condense(["undervote"], profile)

    clean_profile.to_csv(f"{output_folder_base}/NY_mayor_cleaned_votekit.csv")
