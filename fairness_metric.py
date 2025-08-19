from votekit import PreferenceProfile
from votekit.cleaning import remove_and_condense_ranked_profile
from math import comb
from itertools import combinations, product
import numpy as np
from typing import Any, Sequence
from math import pi, sqrt, asin
from voting_rules import ElectionConstructor


def kendall_tau_distance(list1: Sequence[Any], list2: Sequence[Any]) -> int:
    """
    Compute Kendall Tau distance between two rankings (lists).

    Args:
        list1 (list): First ranking (ordered list of candidates).
        list2 (list): Second ranking (ordered list of candidates).

    Returns:
        int: Kendall Tau distance (number of pairwise disagreements).
    """
    list1 = list(list1)
    list2 = list(list2)
    assert len(list1) == len(
        list2
    ), f"Lists must have the same size, found {len(list1)} and {len(list2)} for {list1} and {list2}"

    distance = 0
    n = len(list1)

    # Build position maps for fast lookup
    pos1 = {candidate: idx for idx, candidate in enumerate(list1)}
    pos2 = {candidate: idx for idx, candidate in enumerate(list2)}

    # Check all pairs
    for i in range(n):
        for j in range(i + 1, n):
            cand_i = list1[i]
            cand_j = list1[j]

            # Compare relative order
            if (pos1[cand_i] - pos1[cand_j]) * (pos2[cand_i] - pos2[cand_j]) < 0:
                distance += 1

    return distance


def __unpack_ranking_with_lexicographic_tiebreak(
    ranking: Sequence[frozenset],
) -> tuple[frozenset, ...]:
    """
    A utility function that unpacks a ranking returned by votekit (which may contain ties) into a
    list of individual candidates.  Any ties are resolved in lexicographic order.
    """
    return tuple([frozenset({cand}) for c_set in ranking for cand in sorted(c_set)])


def determine_weighted_ranking_vector_XAB(
    ranking_array: np.ndarray, weight_vector: np.ndarray, a: Any, b: Any
) -> np.ndarray:
    """
    For each voter (row) this will return
        1   if a appears strictly before b,
        0.5 if a and b are both absent   (a_pos == b_pos == ∞),
        0.5 if a and b share the same position,
        0   otherwise,
    and finally multiplies by the per-row weights.

    Args:
        ranking_array (np.ndarray): Array of shape (n_voters, n_candidates) with
            the ranking of each voter for each candidate.
        weight_vector (np.ndarray): Array of shape (n_voters,) with the per-voter
            weights.
        a (Any): Candidate a. Normally a singleton frozenset.
        b (Any): Candidate b. Normally a singleton frozenset.

    Returns:
        np.ndarray: A vector of shape (n_voters,) with the the weighted rankings.
    """
    # element‑wise boolean masks
    is_a = ranking_array == a
    is_b = ranking_array == b

    # first position of a (resp. b) in every row
    # rows that contain no a (resp. b) are marked with np.inf
    a_pos = np.where(is_a.any(axis=1), is_a.argmax(axis=1), np.inf)
    b_pos = np.where(is_b.any(axis=1), is_b.argmax(axis=1), np.inf)

    # 1  if a before b
    # 0.5 if same position *or* both absent
    # 0  otherwise
    xab_vector = np.where(a_pos < b_pos, 1.0, np.where(a_pos == b_pos, 0.5, 0.0))

    return xab_vector * weight_vector


def number_of_voters(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    return float(profile.df["Weight"].sum())


def sigma_UM(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Unanimity Majoritarian (UM) score, which we call sigma_UM here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_UM score which is a value between 0 and 1.
    """

    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        voting_rule(profile=profile, m=n_seats).get_ranking()
    )

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    ranking_array = profile.df[
        [f"Ranking_{i}" for i in range(1, profile.max_ranking_length + 1)]
    ].to_numpy()

    misalignment = 1

    for rank1, rank2 in combinations(original_ranking, 2):
        weighted_ranking_vector = determine_weighted_ranking_vector_XAB(
            ranking_array, weight_vector, rank1, rank2
        )
        alignment_IAB = (1 / n_voters) * np.linalg.norm(weighted_ranking_vector, ord=1)
        misalignment = min(misalignment, alignment_IAB)

    return float((2 / pi) * asin(sqrt(2 * misalignment)) if misalignment < 1 / 2 else 1)


def sigma_IIA(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score,
    which we call sigma_IIA here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    n_candidates = len(profile.candidates)
    ranking_before_unpaking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        ranking_before_unpaking
    )
    total_kendall_distance = 0

    for candidate in profile.candidates:
        original_ranking_without_cand = [
            c_set for c_set in original_ranking if candidate not in c_set
        ]

        voting_ranking_without_cand_before_unpacking = voting_rule(
            remove_and_condense_ranked_profile(candidate, profile), m=n_seats
        ).get_ranking()
        voting_ranking_without_cand = __unpack_ranking_with_lexicographic_tiebreak(
            voting_ranking_without_cand_before_unpacking
        )

        new_dist = kendall_tau_distance(
            original_ranking_without_cand, voting_ranking_without_cand
        )

        total_kendall_distance += new_dist

    return 1 - total_kendall_distance / (n_candidates * comb(n_candidates - 1, 2))


def sigma_IIA_all_subset(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score,
    which we call sigma_IIA here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    n_candidates = len(profile.candidates)
    ranking_before_unpaking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        ranking_before_unpaking
    )
    total_distance = 0

    # NOTE: The Kendall-Tau distance for a subset where all candidates are removed
    # or where no candidates are removed is always 0. Also, when there is only one
    # candidate remaining, the Kendall-Tau distance will always be 0. So we start
    # with subsets of size 1 and go up to n_candidates - 2.
    # So, we will take the distance in these cases to be 0.
    for i in range(1, n_candidates - 1):
        # NOTE: The maximum Kendall-Tau distance for a subset of size n_candidates - i is
        # comb(n_candidates - i, 2)
        subset_divisor = comb(n_candidates - i, 2)
        for candidate_subset in combinations(profile.candidates, i):
            original_ranking_without_cand = [
                c_set
                for c_set in original_ranking
                if not any(cand in c_set for cand in candidate_subset)
            ]

            voting_ranking_without_cand_before_unpacking = voting_rule(
                remove_and_condense_ranked_profile(list(candidate_subset), profile),
                m=min(n_seats, n_candidates - i),
            ).get_ranking()
            voting_ranking_without_cand = __unpack_ranking_with_lexicographic_tiebreak(
                voting_ranking_without_cand_before_unpacking
            )

            new_dist = kendall_tau_distance(
                original_ranking_without_cand, voting_ranking_without_cand
            )

            total_distance += new_dist / subset_divisor

    # NOTE: This is also a viable divisor since the other subsets are trivial.
    # n_subsets = (
    #     2 ** (n_candidates - 1) - 2
    # )  # All subsets of len > 1 that are not the full set
    n_subsets = 2**n_candidates
    return 1 - total_distance / n_subsets


def sigma_IIA_all_subset_v2(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score,
    which we call sigma_IIA here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    n_candidates = len(profile.candidates)
    ranking_before_unpaking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        ranking_before_unpaking
    )
    total_distance = 0

    # NOTE: The Kendall-Tau distance for a subset where all candidates are removed
    # or where no candidates are removed is always 0. Also, when there is only one
    # candidate remaining, the Kendall-Tau distance will always be 0. So we start
    # with subsets of size 1 and go up to n_candidates - 2.
    # So, we will take the distance in these cases to be 0.
    count = 0
    for i in range(1, n_candidates - 1):
        # NOTE: The maximum Kendall-Tau distance for a subset of size i is
        # comb(n_candidates - i, 2)
        subset_divisor = comb(n_candidates - i, 2)
        for candidate_subset in combinations(profile.candidates, i):
            count += 1
            original_ranking_without_cand = [
                c_set
                for c_set in original_ranking
                if not any(cand in c_set for cand in candidate_subset)
            ]

            voting_ranking_without_cand_before_unpacking = voting_rule(
                remove_and_condense_ranked_profile(list(candidate_subset), profile),
                m=min(n_seats, n_candidates - i),
            ).get_ranking()
            voting_ranking_without_cand = __unpack_ranking_with_lexicographic_tiebreak(
                voting_ranking_without_cand_before_unpacking
            )

            new_dist = kendall_tau_distance(
                original_ranking_without_cand, voting_ranking_without_cand
            )

            total_distance += new_dist / subset_divisor

    # NOTE: This is also a viable divisor since the other subsets are trivial.
    # Remove the empty subset, the full set, and the singleton sets.
    n_subsets = (
        2 ** (n_candidates) - 2 - n_candidates
    )  # All subsets of len > 1 that are not the full set
    print(
        f"Count of subsets: {count}, n_subsets: {n_subsets}, total_n_subsets: {2**n_candidates}"
    )
    # n_subsets = 2**n_candidates
    return 1 - total_distance / n_subsets


def sigma_UM_winner_set(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Unanimity Majoritarian (UM) score with respect to the winner set.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_UM score which is a value between 0 and 1.
    """

    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        voting_rule(profile=profile, m=n_seats).get_ranking()
    )

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    ranking_array = profile.df[
        [f"Ranking_{i}" for i in range(1, profile.max_ranking_length + 1)]
    ].to_numpy()

    misalignment = 1

    winners = original_ranking[:n_seats]
    losers = original_ranking[n_seats:]

    for rank1, rank2 in product(winners, losers):
        weighted_ranking_vector = determine_weighted_ranking_vector_XAB(
            ranking_array, weight_vector, rank1, rank2
        )
        alignment_IAB = (1 / n_voters) * np.linalg.norm(weighted_ranking_vector, ord=1)
        misalignment = min(misalignment, alignment_IAB)

    return float((2 / pi) * asin(sqrt(2 * misalignment)) if misalignment < 1 / 2 else 1)


def sigma_IIA_winner_set(
    profile: PreferenceProfile, voting_rule: ElectionConstructor, n_seats: int
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score
    with respect to the winner set.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (PreferenceProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    original_winners_set = set(
        __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(profile=profile, m=n_seats).get_elected()
        )
    )

    total_distance = 0
    for candidate in profile.candidates:
        if n_seats == 1 and frozenset({candidate}) in original_winners_set:
            total_distance += 1
            continue

        # In the n == 1 case, this will always be 1
        new_available_seats = (
            n_seats - 1 if frozenset({candidate}) in original_winners_set else n_seats
        )

        new_winner_set = __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(
                remove_and_condense_ranked_profile(candidate, profile),
                m=new_available_seats,
            ).get_elected()
        )

        total_distance += (
            len(original_winners_set.intersection(new_winner_set)) / new_available_seats
        )

    return total_distance / len(profile.candidates)
