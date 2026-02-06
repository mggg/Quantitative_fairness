# ruff: noqa: E402
from votekit import RankProfile, RankBallot
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parents[1].resolve()
sys.path.append(str(ROOT_DIR))

from voting_metrics_main_code.voting_rules import build_voting_rule  # noqa: E402
from voting_metrics_main_code.fairness_metric import (
    sigma_IIA,
    sigma_IIA_winner_set,
    sigma_UM,
    sigma_UM_winner_set,
)
import numpy as np


condorcet_profile = RankProfile(
    ballots=[
        RankBallot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}]))),
        RankBallot(ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}]))),
        RankBallot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}]))),
    ]
)

basic_IIA_profile = RankProfile(
    ballots=tuple(
        [
            RankBallot(ranking=tuple(map(frozenset, [{"A"}, {"D"}, {"B"}, {"C"}]))),
            RankBallot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"D"}, {"C"}]))),
            RankBallot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}, {"D"}]))),
            RankBallot(ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"A"}, {"B"}]))),
        ]
    )
)

profile_5_cand_ub = RankProfile(
    ballots=tuple(
        [
            RankBallot(
                ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                weight=51,
            ),
            RankBallot(
                ranking=tuple(map(frozenset, [{"E"}, {"B"}, {"A"}, {"C"}, {"D"}])),
                weight=34,
            ),
            RankBallot(
                ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"E"}, {"A"}, {"B"}])),
                weight=15,
            ),
        ]
    )
)

profile_5_cand_mid = RankProfile(
    ballots=tuple(
        [
            RankBallot(
                ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                weight=6,
            ),
            RankBallot(
                ranking=tuple(map(frozenset, [{"C"}, {"D"}, {"E"}, {"A"}, {"B"}])),
                weight=4,
            ),
        ]
    )
)


def make_random_profile(n_voters: int, cand_list: list[str]) -> RankProfile:
    weights = np.unique_counts(list(map(int, np.random.gamma(5, 1, n_voters))))[1]

    n_cands = len(cand_list)
    all_cand_set = set(map(lambda x: frozenset({x}), cand_list))
    ballot_list = []
    for wt in weights:
        ranking = list(
            map(
                lambda x: frozenset({str(x)}),
                np.random.choice(
                    cand_list,
                    size=np.random.randint(1, len(cand_list)),
                    replace=False,
                ),
            )
        )
        if len(ranking) == n_cands - 1:
            ranking.append(*(all_cand_set - set(ranking)))

        ballot_list.append(
            RankBallot(
                ranking=tuple(ranking),
                weight=wt,
            )
        )

    return RankProfile(ballots=tuple(ballot_list), candidates=tuple(cand_list))


# def test_random_profiles():
#     n_tests = 100
#     n_voters = 100
#     cand_list = ["A", "B", "C", "D"]
#     n_cands = len(cand_list)
#     n_seats = 2
#
#     from tqdm import tqdm
#     from itertools import product
#
#     for _, variant in tqdm(
#         product(list(range(n_tests)), ["worst_case", "average"]), total=n_tests * 2
#     ):
#         profile = make_random_profile(n_voters, cand_list)
#         voting_rule = build_voting_rule(n_cands, "borda")
#         for interp_type in ["asin", "odds"]:
#             assert (
#                 0
#                 <= sigma_UM(
#                     profile,
#                     voting_rule,
#                     n_seats,
#                     variant=variant,
#                     interpolation_type=interp_type,
#                 )
#                 <= 1
#             )
#             assert (
#                 0
#                 <= sigma_UM_winner_set(
#                     profile,
#                     voting_rule,
#                     n_seats,
#                     variant=variant,
#                     interpolation_type=interp_type,
#                 )
#                 <= 1
#             )
#         assert 0 <= sigma_IIA(profile, voting_rule, n_seats, variant=variant) <= 1
#         assert (
#             0
#             <= sigma_IIA_all_subset(profile, voting_rule, n_seats, variant=variant)
#             <= 1
#         )
#         assert (
#             0
#             <= sigma_IIA_winner_set(profile, voting_rule, n_seats, variant=variant)
#             <= 1
#         )
#
#         voting_rule = build_voting_rule(n_cands, "plurality")
#         for interp_type in ["asin", "odds"]:
#             assert (
#                 0
#                 <= sigma_UM(
#                     profile,
#                     voting_rule,
#                     n_seats,
#                     variant=variant,
#                     interpolation_type=interp_type,
#                 )
#                 <= 1
#             )
#             assert (
#                 0
#                 <= sigma_UM_winner_set(
#                     profile,
#                     voting_rule,
#                     n_seats,
#                     variant=variant,
#                     interpolation_type=interp_type,
#                 )
#                 <= 1
#             )
#         assert 0 <= sigma_IIA(profile, voting_rule, n_seats, variant=variant) <= 1
#         assert (
#             0
#             <= sigma_IIA_all_subset(profile, voting_rule, n_seats, variant=variant)
#             <= 1
#         )
#         assert (
#             0
#             <= sigma_IIA_winner_set(profile, voting_rule, n_seats, variant=variant)
#             <= 1
#         )


def test_condorcet_profile_borda():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "borda")
    assert (
        abs(
            sigma_UM(
                condorcet_profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.608
        )
        < 1e-3
    )


def test_condorcet_profile_3_approval():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "3-approval")
    assert (
        abs(
            sigma_UM(
                condorcet_profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.608
        )
        < 1e-3
    )


def test_condorcet_profile_2_approval():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "2-approval")
    assert (
        abs(
            sigma_UM(
                condorcet_profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.608
        )
        < 1e-3
    )


def test_condorcet_profile_plurality():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "plurality")
    assert (
        abs(
            sigma_UM(
                condorcet_profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.608
        )
        < 1e-3
    )


def test_low_UM_plurality():
    n_cands = 3
    n_seats = 1
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"C"}, {"B"}])), weight=99
                ),
                RankBallot(ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}]))),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "plurality")
    assert (
        abs(
            sigma_UM(
                profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.0903
        )
        < 1e-4
    )


def test_IIA_Borda_high():
    voting_rule = build_voting_rule(4, "borda")
    assert (
        abs(sigma_IIA(basic_IIA_profile, voting_rule, 1, variant="average") - 0.917)
        < 1e-3
    )


def test_IIA_Plurality_high_needs_lex_tiebreak_due_to_tie_in_final_ranking():
    voting_rule = build_voting_rule(4, "plurality")
    assert (
        abs(sigma_IIA(basic_IIA_profile, voting_rule, 1, variant="average") - 0.833)
        < 1e-3
    )


def test_IIA_Plurality_high_needs_borda_tiebreak():
    voting_rule = build_voting_rule(4, "plurality", tiebreak="borda")

    assert (
        abs(sigma_IIA(basic_IIA_profile, voting_rule, 2, variant="average") - 0.917)
        < 1e-3
    )


def test_IIA_winner_set_STV_ub():
    n_cands = 3
    n_seats = 1
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=7
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}])), weight=2
                ),
                RankBallot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}]))),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "stv")
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, n_seats, variant="average") - 1)
        < 1e-4
    )


def test_IIA_winner_set_STV_mid():
    n_cands = 3
    n_seats = 2
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=6
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=4
                ),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "stv")
    assert (
        abs(
            sigma_IIA_winner_set(profile, voting_rule, n_seats, variant="average")
            - 2 / 3.0
        )
        < 1e-4
    )


def test_UM_borda_ub():
    n_cands = 3
    n_seats = 1

    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=5
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}])), weight=3
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=2
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(n_cands, "borda")
    assert (
        abs(
            sigma_UM(
                profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 1.0
        )
        < 1e-3
    )


def test_UM_plurality_ub():
    n_cands = 3
    n_seats = 1

    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=5
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}])), weight=3
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=2
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(n_cands, "plurality")
    assert (
        abs(
            sigma_UM(
                profile,
                voting_rule,
                n_seats,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 1.0
        )
        < 1e-3
    )


def test_UM_4_cands_STV():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}])),
                    weight=5,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}, {"D"}])),
                    weight=3,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"A"}, {"B"}])),
                    weight=2,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(4, "stv")
    assert (
        abs(
            sigma_UM(
                profile, voting_rule, 1, variant="worst_case", interpolation_type="asin"
            )
            - 0.436
        )
        < 1e-3
    )


def test_UM_winner_set_changes_with_seat_number_STV():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}])),
                    weight=5,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}, {"D"}])),
                    weight=3,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"A"}, {"B"}])),
                    weight=2,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(4, "stv")
    assert (
        abs(
            sigma_UM_winner_set(
                profile, voting_rule, 1, variant="worst_case", interpolation_type="asin"
            )
            - 1
        )
        < 1e-3
    )
    assert (
        abs(
            sigma_UM_winner_set(
                profile, voting_rule, 2, variant="worst_case", interpolation_type="asin"
            )
            - 1
        )
        < 1e-3
    )
    assert (
        abs(
            sigma_UM_winner_set(
                profile, voting_rule, 3, variant="worst_case", interpolation_type="asin"
            )
            - 0.436
        )
        < 1e-3
    )


def test_IIA_winner_set_5_cand_STV_ub():

    voting_rule = build_voting_rule(4, "stv")
    assert (
        abs(
            sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1, variant="average")
            - 1
        )
        < 1e-3
    )


def test_IIA_winner_set_5_cand_Plurality_ub():

    voting_rule = build_voting_rule(4, "plurality")
    assert (
        abs(
            sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1, variant="average")
            - 1
        )
        < 1e-3
    )


def test_IIA_winner_set_5_cand_Borda_ub():

    voting_rule = build_voting_rule(4, "borda")
    assert (
        abs(
            sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1, variant="average")
            - 1
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_STV_ub():

    voting_rule = build_voting_rule(4, "stv")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_ub,
                voting_rule,
                1,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 1
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_Plurality_ub():

    voting_rule = build_voting_rule(4, "plurality")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_ub,
                voting_rule,
                1,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 1
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_Borda_ub():
    voting_rule = build_voting_rule(4, "borda")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_ub,
                voting_rule,
                1,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 1
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_STV_mid():
    voting_rule = build_voting_rule(4, "stv")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_mid,
                voting_rule,
                2,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.705
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_Plurality_mid():
    voting_rule = build_voting_rule(4, "plurality")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_mid,
                voting_rule,
                2,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.705
        )
        < 1e-3
    )


def test_UM_winner_set_5_cand_Borda_mid():
    voting_rule = build_voting_rule(4, "borda")
    assert (
        abs(
            sigma_UM_winner_set(
                profile_5_cand_mid,
                voting_rule,
                2,
                variant="worst_case",
                interpolation_type="asin",
            )
            - 0.705
        )
        < 1e-3
    )


def test_IIA_winner_set_changes_with_election_type():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                    weight=6,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"D"}, {"E"}, {"A"}, {"B"}])),
                    weight=4,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(5, "stv")
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 2, variant="average") - 0.8)
        < 1e-3
    )

    voting_rule = build_voting_rule(5, "plurality")
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 2, variant="average") - 0.8)
        < 1e-3
    )

    voting_rule = build_voting_rule(5, "borda")
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 2, variant="average") - 1.0)
        < 1e-3
    )


def test_IIA_winner_set_changes_with_seat_number_Plurality():

    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(
                        map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}, {"F"}])
                    ),
                    weight=8,
                ),
                RankBallot(
                    ranking=tuple(
                        map(frozenset, [{"D"}, {"A"}, {"B"}, {"C"}, {"E"}, {"F"}])
                    ),
                    weight=7,
                ),
                RankBallot(
                    ranking=tuple(
                        map(frozenset, [{"C"}, {"A"}, {"B"}, {"F"}, {"E"}, {"D"}])
                    ),
                    weight=5,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(6, "plurality")
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 1, variant="average") - 1) < 1e-3
    )
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 2, variant="average") - 0.833)
        < 1e-3
    )
    assert (
        abs(sigma_IIA_winner_set(profile, voting_rule, 3, variant="average") - 0.917)
        < 1e-3
    )


def test_IIA_Plurality_obtains_zero():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"C"}, {"B"}])), weight=4
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}])), weight=3
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"B"}, {"A"}])), weight=2
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(3, "plurality")
    assert sigma_IIA(profile, voting_rule, 1, variant="average") == 0.0


def test_IIA_winner_set_Plurality_obtains_lb():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"C"}, {"B"}])), weight=4
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}])), weight=3
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"B"}, {"A"}])), weight=2
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(3, "plurality")
    assert sigma_IIA_winner_set(profile, voting_rule, 1, variant="average") == 0.0


def test_IIA_winner_set_Plurality_low():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"C"}, {"B"}])), weight=4
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}])), weight=3
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"B"}, {"A"}])), weight=2
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(3, "plurality")
    assert sigma_IIA_winner_set(profile, voting_rule, 2, variant="average") == 1 / 3.0


def test_UM_Plurality_low():
    profile = RankProfile(
        ballots=tuple(
            [
                RankBallot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}])),
                    weight=10,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}, {"D"}])),
                    weight=3,
                ),
                RankBallot(
                    ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}, {"D"}])),
                    weight=2,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(4, "plurality")
    assert (
        abs(
            sigma_UM(
                profile, voting_rule, 1, variant="worst_case", interpolation_type="asin"
            )
            - 0.436
        )
        < 1e-3
    )
