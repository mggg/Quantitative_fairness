from votekit import RankProfile
from votekit.cleaning import remove_and_condense_rank_profile
from math import comb
from itertools import combinations, product
import numpy as np
from typing import Any, Sequence
from math import pi, sqrt, asin
from voting_metrics_main_code.voting_rules import ElectionConstructor


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


def number_of_voters(profile: RankProfile, *args, **kwargs) -> float:
    del args, kwargs  # unused
    return float(profile.df["Weight"].sum())


# =================================================================================================
#                                            SIGMA UM
# =================================================================================================


def __asin_interpolation(misalignment: float) -> float:
    return float((2 / pi) * asin(sqrt(2 * misalignment)) if misalignment < 1 / 2 else 1)


def __odds_interpolation(misalignment: float) -> float:
    return float(misalignment / (1 - misalignment) if misalignment < 1 / 2 else 1)


def __linear_interpolation(misalignment: float) -> float:
    return float(2 * misalignment if misalignment < 1 / 2 else 1)


def sigma_UM(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "worst_case",
    interpolation_type: str = "asin",
) -> float:
    """
    Computes the extended Unanimity Majoritarian (UM) score, which we call sigma_UM here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_UM score which is a value between 0 and 1.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    match interpolation_type:
        case "linear":
            interpolation_fn = __linear_interpolation
        case "asin":
            interpolation_fn = __asin_interpolation
        case "odds":
            interpolation_fn = __odds_interpolation
        case _:
            raise ValueError(
                f"Unknown interpolation_type: {interpolation_type}. Must be 'asin', 'odds', or 'linear'."
            )

    raw_ranking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(raw_ranking)

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    ranking_array = profile.df[
        [f"Ranking_{i}" for i in range(1, profile.max_ranking_length + 1)]
    ].to_numpy()

    misalignment = 1
    total_alignment = 0
    for rank1, rank2 in combinations(original_ranking, 2):
        weighted_ranking_vector = determine_weighted_ranking_vector_XAB(
            ranking_array, weight_vector, rank1, rank2
        )
        alignment_IAB = (1 / n_voters) * np.linalg.norm(weighted_ranking_vector, ord=1)
        misalignment = min(misalignment, alignment_IAB)
        total_alignment += interpolation_fn(alignment_IAB)

    average_alignment = total_alignment / comb(len(original_ranking), 2)

    return average_alignment if variant == "average" else interpolation_fn(misalignment)


def sigma_UM_winner_set(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "worst_case",
    interpolation_type: str = "asin",
) -> float:
    """
    Computes the extended Unanimity Majoritarian (UM) score with respect to the winner set.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_UM score which is a value between 0 and 1.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    match interpolation_type:
        case "linear":
            interpolation_fn = __linear_interpolation
        case "asin":
            interpolation_fn = __asin_interpolation
        case "odds":
            interpolation_fn = __odds_interpolation
        case _:
            raise ValueError(
                f"Unknown interpolation_type: {interpolation_type}. Must be 'asin', 'odds', or 'linear'."
            )

    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        voting_rule(profile=profile, m=n_seats).get_ranking()
    )

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    ranking_array = profile.df[
        [f"Ranking_{i}" for i in range(1, profile.max_ranking_length + 1)]
    ].to_numpy()

    misalignment = 1
    total_alignment = 0
    winners = original_ranking[:n_seats]
    losers = original_ranking[n_seats:]

    for rank1, rank2 in product(winners, losers):
        weighted_ranking_vector = determine_weighted_ranking_vector_XAB(
            ranking_array, weight_vector, rank1, rank2
        )
        alignment_IAB = (1 / n_voters) * np.linalg.norm(weighted_ranking_vector, ord=1)
        misalignment = min(misalignment, alignment_IAB)
        total_alignment += interpolation_fn(alignment_IAB)

    average_misalignment = total_alignment / (
        n_seats * (len(original_ranking) - n_seats)
    )

    return (
        average_misalignment if variant == "average" else interpolation_fn(misalignment)
    )


# =================================================================================================
#                                            SIGMA IIA
# =================================================================================================


def sigma_IIA(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "average",
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score,
    which we call sigma_IIA here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """

    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    n_candidates = len(profile.candidates)
    ranking_before_unpaking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        ranking_before_unpaking
    )
    total_kendall_distance = 0
    largest_kendall_distance = 0
    distance_divisor = comb(n_candidates - 1, 2)

    for candidate in profile.candidates:
        original_ranking_without_cand = [
            c_set for c_set in original_ranking if candidate not in c_set
        ]

        voting_ranking_without_cand_before_unpacking = voting_rule(
            remove_and_condense_rank_profile(candidate, profile), m=n_seats
        ).get_ranking()
        voting_ranking_without_cand = __unpack_ranking_with_lexicographic_tiebreak(
            voting_ranking_without_cand_before_unpacking
        )

        new_dist = (
            kendall_tau_distance(
                original_ranking_without_cand, voting_ranking_without_cand
            )
            / distance_divisor
        )

        total_kendall_distance += new_dist
        largest_kendall_distance = max(largest_kendall_distance, new_dist)

    if variant == "worst_case":
        return 1 - largest_kendall_distance
    return 1 - total_kendall_distance / (n_candidates)


def sigma_IIA_all_subset(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "average",
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score,
    which we call sigma_IIA here.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """

    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    n_candidates = len(profile.candidates)
    ranking_before_unpaking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        ranking_before_unpaking
    )
    total_distance = 0
    largest_distance = 0

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
                remove_and_condense_rank_profile(list(candidate_subset), profile),
                m=min(n_seats, n_candidates - i),
            ).get_ranking()
            voting_ranking_without_cand = __unpack_ranking_with_lexicographic_tiebreak(
                voting_ranking_without_cand_before_unpacking
            )

            new_dist = (
                kendall_tau_distance(
                    original_ranking_without_cand, voting_ranking_without_cand
                )
                / subset_divisor
            )

            total_distance += new_dist
            largest_distance = max(largest_distance, new_dist)

    if variant == "worst_case":
        return 1 - largest_distance

    n_subsets = (
        2 ** (n_candidates) - 2 - n_candidates
    )  # All subsets of len > 1 that are not the full set
    return 1 - total_distance / n_subsets


def sigma_IIA_winner_set(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "average",
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score
    with respect to the winner set.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    n_candidates = len(profile.candidates)
    if n_candidates == n_seats:
        return 1.0

    if n_candidates == 2 and n_seats == 1:
        return 1.0

    if n_seats < 1:
        raise ValueError(f"Number of seats must be at least 1, found {n_seats}.")
    if n_seats > n_candidates:
        raise ValueError(
            f"Number of seats must be at most the number of candidates, found {n_seats} seats and {n_candidates} candidates."
        )

    original_winners_set = set(
        __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(profile=profile, m=n_seats).get_elected()
        )
    )

    total_distance = 0
    smallest_normalized_intersection = 1

    for candidate in profile.candidates:
        singleton = set({frozenset({candidate})})
        if singleton == original_winners_set:
            continue

        # In the n == 1 case, this will always be 1
        new_available_seats = n_seats - len(
            singleton.intersection(original_winners_set)
        )

        new_winner_set = __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(
                remove_and_condense_rank_profile(candidate, profile),
                m=new_available_seats,
            ).get_elected()
        )
        new_dist = (
            len(original_winners_set.intersection(new_winner_set)) / new_available_seats
        )

        total_distance += new_dist
        smallest_normalized_intersection = min(
            smallest_normalized_intersection, new_dist
        )

    if variant == "worst_case":
        return smallest_normalized_intersection

    n_subsets_considered = len(profile.candidates) - (
        1 if len(original_winners_set) == 1 else 0
    )

    return total_distance / n_subsets_considered


def sigma_IIA_winner_set_all_subset(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: str = "average",
) -> float:
    """
    Computes the extended Independence of Irrelevant Alternatives (IIA) score
    with respect to the winner set.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): The preference profile to score.
        voting_rule (Election): The voting rule to apply to the profile.

    Returns:
        float: The sigma_IIA score which is a value between 0 and 1.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(
            f"Unknown variant: {variant}. Must be 'average' or 'worst_case'."
        )

    original_winners_set = set(
        __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(profile=profile, m=n_seats).get_elected()
        )
    )

    full_candidate_set = set(frozenset({cand}) for cand in profile.candidates)
    n_candidates = len(profile.candidates)

    if n_candidates == n_seats:
        return 1.0
    if n_candidates == 2 and n_seats == 1:
        return 1.0

    if n_seats < 1:
        raise ValueError(f"Number of seats must be at least 1, found {n_seats}.")
    if n_seats > n_candidates:
        raise ValueError(
            f"Number of seats must be at most the number of candidates, found {n_seats} seats and {n_candidates} candidates."
        )

    total_distance = 0
    smallest_normalized_intersection = 1

    # NOTE: Don't need to consider the whole set because we want for W \nsubseteq S
    # and the whole set will always contain W.
    for i in range(1, n_candidates):
        for candidate_subset in combinations(profile.candidates, i):
            candidate_subset_set = set(frozenset({cand}) for cand in candidate_subset)

            if original_winners_set.issubset(
                candidate_subset_set
            ) or candidate_subset_set == (full_candidate_set - original_winners_set):
                continue

            new_available_seats = n_seats - len(
                candidate_subset_set.intersection(original_winners_set)
            )

            new_winner_set = __unpack_ranking_with_lexicographic_tiebreak(
                voting_rule(
                    remove_and_condense_rank_profile(list(candidate_subset), profile),
                    m=new_available_seats,
                ).get_elected()
            )

            new_dist = (
                len(original_winners_set.intersection(new_winner_set))
                / new_available_seats
            )

            total_distance += new_dist
            smallest_normalized_intersection = min(
                smallest_normalized_intersection, new_dist
            )

    if variant == "worst_case":
        return smallest_normalized_intersection

    n_subsets_considered = 2**n_candidates - 2 ** (n_candidates - n_seats) - 2

    return total_distance / n_subsets_considered
