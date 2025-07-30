from votekit.ballot_generator import name_BradleyTerry
from votekit import PreferenceInterval
from pathlib import Path
from itertools import product
from joblib import Parallel, delayed
from joblib_progress import joblib_progress


def generate_and_save_profile(n_cands, n_voters, alpha, idx, output_base_dir):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    bg = name_BradleyTerry(
        cohesion_parameters={"bloc_1": {"bloc_1": 1.0}},
        candidates=list(range(n_cands)),
        bloc_voter_prop={"bloc_1": 1.0},
        pref_intervals_by_bloc={
            "bloc_1": PreferenceInterval.from_dirichlet(
                candidates=list(alphabet[:n_cands]),
                alpha=alpha,
            )
        },
    )
    prof = bg.generate_profile(n_voters)
    output_dir = f"{output_base_dir}/{n_cands:02d}/alpha_{alpha:.2f}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    prof.to_csv(f"{output_dir}/profile_{idx}.csv")


if __name__ == "__main__":
    cand_list = [6, 7, 8, 9]
    alpha_list = [1 / 3, 1 / 2, 1, 2, 3]
    n_voters = 15_000
    n_samples = 1000
    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of profiles are not overwritten.
    output_base_dir = str(Path("./preference_profiles_v2/").resolve())

    with joblib_progress(
        "Generating profiles", total=n_samples * len(cand_list) * len(alpha_list)
    ):
        Parallel(n_jobs=20)(
            delayed(generate_and_save_profile)(
                n_cands, n_voters, alpha, i, output_base_dir
            )
            for n_cands, alpha, i in product(
                cand_list, alpha_list, list(range(n_samples))
            )
        )
