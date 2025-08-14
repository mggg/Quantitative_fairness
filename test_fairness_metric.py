from votekit import PreferenceProfile, Ballot
from voting_rules import build_voting_rule
from fairness_metric import (
    sigma_IIA,
    sigma_UM,
    sigma_IIA_winner_set,
    sigma_UM_winner_set,
)
import numpy as np


condorcet_profile = PreferenceProfile(
    ballots=tuple(
        [
            Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}]))),
            Ballot(ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}]))),
            Ballot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}]))),
        ]
    )
)


profile_5_cand_ub = PreferenceProfile(
    ballots=tuple(
        [
            Ballot(
                ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                weight=51,
            ),
            Ballot(
                ranking=tuple(map(frozenset, [{"E"}, {"B"}, {"A"}, {"C"}, {"D"}])),
                weight=34,
            ),
            Ballot(
                ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"E"}, {"A"}, {"B"}])),
                weight=15,
            ),
        ]
    )
)

profile_5_cand_mid = PreferenceProfile(
    ballots=tuple(
        [
            Ballot(
                ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                weight=6,
            ),
            Ballot(
                ranking=tuple(map(frozenset, [{"C"}, {"D"}, {"E"}, {"A"}, {"B"}])),
                weight=4,
            ),
        ]
    )
)


def make_random_profile(n_voters: int, cand_list: list[str]) -> PreferenceProfile:
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
            Ballot(
                ranking=tuple(ranking),
                weight=wt,
            )
        )

    return PreferenceProfile(ballots=tuple(ballot_list), candidates=tuple(cand_list))


def test_condorcet_profile_borda():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "borda")
    assert abs(sigma_UM(condorcet_profile, voting_rule, n_seats) - 0.608) < 1e-3


def test_condorcet_profile_3_approval():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "3-approval")
    assert abs(sigma_UM(condorcet_profile, voting_rule, n_seats) - 0.608) < 1e-3


def test_condorcet_profile_2_approval():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "2-approval")
    assert abs(sigma_UM(condorcet_profile, voting_rule, n_seats) - 0.608) < 1e-3


def test_condorcet_profile_plurality():
    n_cands = 3
    n_seats = 1
    voting_rule = build_voting_rule(n_cands, "plurality")
    assert abs(sigma_UM(condorcet_profile, voting_rule, n_seats) - 0.608) < 1e-3


def test_low_UM_plurality():
    n_cands = 3
    n_seats = 1
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(ranking=tuple(map(frozenset, [{"A"}, {"C"}, {"B"}])), weight=99),
                Ballot(ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}]))),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "plurality")
    assert abs(sigma_UM(profile, voting_rule, n_seats) - 0.0903) < 1e-4


def test_IIA_winner_set_STV_ub():
    n_cands = 3
    n_seats = 1
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=7),
                Ballot(ranking=tuple(map(frozenset, [{"B"}, {"C"}, {"A"}])), weight=2),
                Ballot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}]))),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "stv")
    assert abs(sigma_IIA_winner_set(profile, voting_rule, n_seats) - 1) < 1e-4


def test_IIA_winner_set_STV_mid():
    n_cands = 3
    n_seats = 2
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=6),
                Ballot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=4),
            ]
        )
    )
    voting_rule = build_voting_rule(n_cands, "stv")
    assert abs(sigma_IIA_winner_set(profile, voting_rule, n_seats) - 2 / 3.0) < 1e-4


def test_UM_borda_ub():
    n_cands = 3
    n_seats = 1

    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=5),
                Ballot(ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}])), weight=3),
                Ballot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=2),
            ]
        )
    )

    voting_rule = build_voting_rule(n_cands, "borda")
    assert abs(sigma_UM(profile, voting_rule, n_seats) - 1.0) < 1e-3


def test_UM_plurality_ub():
    n_cands = 3
    n_seats = 1

    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}])), weight=5),
                Ballot(ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}])), weight=3),
                Ballot(ranking=tuple(map(frozenset, [{"C"}, {"A"}, {"B"}])), weight=2),
            ]
        )
    )

    voting_rule = build_voting_rule(n_cands, "plurality")
    assert abs(sigma_UM(profile, voting_rule, n_seats) - 1.0) < 1e-3


def test_UM_4_cands_STV():
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}])),
                    weight=5,
                ),
                Ballot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}, {"D"}])),
                    weight=3,
                ),
                Ballot(
                    ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"A"}, {"B"}])),
                    weight=2,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(4, "stv")
    assert abs(sigma_UM(profile, voting_rule, 1) - 0.436) < 1e-3


def test_UM_winner_set_changes_with_seat_number_STV():
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}])),
                    weight=5,
                ),
                Ballot(
                    ranking=tuple(map(frozenset, [{"B"}, {"A"}, {"C"}, {"D"}])),
                    weight=3,
                ),
                Ballot(
                    ranking=tuple(map(frozenset, [{"D"}, {"C"}, {"A"}, {"B"}])),
                    weight=2,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(4, "stv")
    assert abs(sigma_UM_winner_set(profile, voting_rule, 1) - 1) < 1e-3
    assert abs(sigma_UM_winner_set(profile, voting_rule, 2) - 1) < 1e-3
    assert abs(sigma_UM_winner_set(profile, voting_rule, 3) - 0.436) < 1e-3


def test_IIA_winner_set_5_cand_STV_ub():

    voting_rule = build_voting_rule(4, "stv")
    assert abs(sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_IIA_winner_set_5_cand_Plurality_ub():

    voting_rule = build_voting_rule(4, "plurality")
    assert abs(sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_IIA_winner_set_5_cand_Borda_ub():

    voting_rule = build_voting_rule(4, "borda")
    assert abs(sigma_IIA_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_UM_winner_set_5_cand_STV_ub():

    voting_rule = build_voting_rule(4, "stv")
    assert abs(sigma_UM_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_UM_winner_set_5_cand_Plurality_ub():

    voting_rule = build_voting_rule(4, "plurality")
    assert abs(sigma_UM_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_UM_winner_set_5_cand_Borda_ub():
    voting_rule = build_voting_rule(4, "borda")
    assert abs(sigma_UM_winner_set(profile_5_cand_ub, voting_rule, 1) - 1) < 1e-3


def test_UM_winner_set_5_cand_STV_mid():
    voting_rule = build_voting_rule(4, "stv")
    assert abs(sigma_UM_winner_set(profile_5_cand_mid, voting_rule, 2) - 0.705) < 1e-3


def test_UM_winner_set_5_cand_Plurality_mid():
    voting_rule = build_voting_rule(4, "plurality")
    assert abs(sigma_UM_winner_set(profile_5_cand_mid, voting_rule, 2) - 0.705) < 1e-3


def test_UM_winner_set_5_cand_Borda_mid():
    voting_rule = build_voting_rule(4, "borda")
    assert abs(sigma_UM_winner_set(profile_5_cand_mid, voting_rule, 2) - 0.705) < 1e-3


def test_IIA_winner_set_changes_with_election_type():
    profile = PreferenceProfile(
        ballots=tuple(
            [
                Ballot(
                    ranking=tuple(map(frozenset, [{"A"}, {"B"}, {"C"}, {"D"}, {"E"}])),
                    weight=6,
                ),
                Ballot(
                    ranking=tuple(map(frozenset, [{"C"}, {"D"}, {"E"}, {"A"}, {"B"}])),
                    weight=4,
                ),
            ]
        )
    )

    voting_rule = build_voting_rule(5, "stv")
    assert abs(sigma_IIA_winner_set(profile, voting_rule, 2) - 0.8) < 1e-3

    voting_rule = build_voting_rule(5, "plurality")
    assert abs(sigma_IIA_winner_set(profile, voting_rule, 2) - 0.8) < 1e-3

    voting_rule = build_voting_rule(5, "borda")
    assert abs(sigma_IIA_winner_set(profile, voting_rule, 2) - 1.0) < 1e-3
