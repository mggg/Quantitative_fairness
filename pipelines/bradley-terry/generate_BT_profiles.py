from votekit.ballot_generator import BlocSlateConfig
import votekit.ballot_generator as bg
from votekit import PreferenceInterval, PreferenceProfile
from pathlib import Path
from itertools import product
from joblib import Parallel, delayed
from joblib_progress import joblib_progress


def generate_and_save_profile(
    n_a_cands,
    n_b_cands,
    n_voters,
    b_proportion,
    a_cohesion,
    b_cohesion,
    aa_alpha,
    ab_alpha,
    ba_alpha,
    bb_alpha,
    idx,
    output_base_dir,
):
    slate_to_candidates = {
        "bloc_1": [f"A{i + 1}" for i in range(n_a_cands)],
        "bloc_2": [f"B{i + 1}" for i in range(n_b_cands)],
    }
    config = BlocSlateConfig(
        n_voters=n_voters,
        slate_to_candidates=slate_to_candidates,
        cohesion_mapping={
            "bloc_1": {"bloc_1": a_cohesion, "bloc_2": 1 - a_cohesion},
            "bloc_2": {"bloc_1": 1 - b_cohesion, "bloc_2": b_cohesion},
        },
        bloc_proportions={"bloc_1": 1 - b_proportion, "bloc_2": b_proportion},
        preference_mapping={
            "bloc_1": {
                "bloc_1": PreferenceInterval.from_dirichlet(
                    candidates=slate_to_candidates["bloc_1"],
                    alpha=aa_alpha,
                ),
                "bloc_2": PreferenceInterval.from_dirichlet(
                    candidates=slate_to_candidates["bloc_2"],
                    alpha=ab_alpha,
                ),
            },
            "bloc_2": {
                "bloc_1": PreferenceInterval.from_dirichlet(
                    candidates=slate_to_candidates["bloc_1"],
                    alpha=ba_alpha,
                ),
                "bloc_2": PreferenceInterval.from_dirichlet(
                    candidates=slate_to_candidates["bloc_2"],
                    alpha=bb_alpha,
                ),
            },
        },
    )
    prof = bg.slate_bt_profile_generator(config)
    output_dir = (
        f"{output_base_dir}/"
        f"{n_a_cands:02d}_{n_b_cands:02d}/"
        f"b_proportion_{b_proportion}"
        f"__ALPHA_({aa_alpha:.2f},{ab_alpha:.2f},{ba_alpha:.2f},{bb_alpha:.2f})"
        f"__COHESION_({a_cohesion:.2f},{b_cohesion:.2f})"
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    assert isinstance(prof, PreferenceProfile)
    prof.to_csv(f"{output_dir}/profile_{idx}.csv")


if __name__ == "__main__":
    n_voters = 15_000
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

    # NOTE: Change this to your desired output directory. I changed it
    # already to make sure that the first set of profiles are not overwritten.
    output_base_dir = str(
        Path(f"{__file__}").parents[2] / Path("data/preference_profiles/").resolve()
    )

    with joblib_progress(
        "Generating profiles",
        total=n_samples
        * len(b_bloc_proportions)
        * len(alpha_combinations)
        * len(cohesion_combinations)
        * len(candidate_count_combinations),
    ):
        Parallel(n_jobs=20)(
            delayed(generate_and_save_profile)(
                n_a_cands=n_a_cands,
                n_b_cands=n_b_cands,
                n_voters=n_voters,
                b_proportion=b_bloc_proportion,
                a_cohesion=a_coh,
                b_cohesion=b_coh,
                aa_alpha=aa_al,
                ab_alpha=ab_al,
                ba_alpha=ba_al,
                bb_alpha=bb_al,
                idx=i,
                output_base_dir=output_base_dir,
            )
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
            )
        )
