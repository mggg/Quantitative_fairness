"""Compute unanimity and independence scores for rankings and winner sets.

Ranking metrics retain the historical ``sigma`` names in code; the manuscript denotes them
by rho. Functions suffixed ``_winner_set`` score elected candidates rather than full rankings.
"""

from collections.abc import Callable, Hashable, Iterable, Sequence
from itertools import combinations, product
from math import asin, comb, pi, sqrt

import numpy as np
from numpy.typing import NDArray
from votekit import RankProfile
from votekit.cleaning import remove_and_condense_rank_profile

from voting_metrics_main_code.constants import InterpolationType, MetricVariant
from voting_metrics_main_code.voting_rules import ElectionConstructor, random_candidate_order


def kendall_tau_distance(list1: Sequence[Hashable], list2: Sequence[Hashable]) -> int:
    """Count pairwise order disagreements between two untied rankings.

    The rankings must contain the same distinct, hashable candidates. Singleton frozensets from
    VoteKit rankings are valid candidate values.

    Args:
        list1 (Sequence[Hashable]): First candidate ordering.
        list2 (Sequence[Hashable]): Second ordering of the same candidates.

    Returns:
        int: Number of candidate pairs whose relative order differs.

    Raises:
        AssertionError: The rankings have different lengths.
        KeyError: A candidate in the first ranking is absent from the second.
    """
    list1 = list(list1)
    list2 = list(list2)
    assert len(list1) == len(list2), (
        f"Lists must have the same size, found {len(list1)} and {len(list2)} for {list1} and"
        f" {list2}"
    )

    distance = 0
    n = len(list1)

    pos1 = {candidate: idx for idx, candidate in enumerate(list1)}
    pos2 = {candidate: idx for idx, candidate in enumerate(list2)}

    for i in range(n):
        for j in range(i + 1, n):
            cand_i = list1[i]
            cand_j = list1[j]

            if (pos1[cand_i] - pos1[cand_j]) * (pos2[cand_i] - pos2[cand_j]) < 0:
                distance += 1

    return distance


def __unpack_ranking_with_lexicographic_tiebreak(
    ranking: Sequence[frozenset[str]],
) -> tuple[frozenset[str], ...]:
    """Break each tied rank into lexicographically ordered singleton candidate sets.

    Args:
        ranking (Sequence[frozenset[str]]): Ordered candidate sets, with ties within each set.

    Returns:
        tuple[frozenset[str], ...]: Untied ranking preserving the order between the original ranks.
    """
    return tuple([frozenset({cand}) for c_set in ranking for cand in sorted(c_set)])


def determine_weighted_ranking_vector_XAB(
    ranking_array: NDArray[np.object_],
    weight_vector: NDArray[np.float64],
    a: frozenset[str],
    b: frozenset[str],
) -> NDArray[np.float64]:
    """Weight each ballot's support for placing candidate a ahead of candidate b.

    A row contributes its full weight if a appears first, half its weight if both candidates are
    absent or occupy the same position, and zero otherwise. Comparisons match complete ranking
    cells: a tied set containing a candidate does not equal that candidate's singleton set.

    Args:
        ranking_array (NDArray[np.object_]): Ranking cells of shape (n_ballots, n_positions),
            ordered from first to last preference. At least one position is required.
        weight_vector (NDArray[np.float64]): Nonnegative ballot weights of shape (n_ballots,).
        a (frozenset[str]): Singleton set containing the first candidate.
        b (frozenset[str]): Singleton set containing the second candidate.

    Returns:
        NDArray[np.float64]: Weighted pairwise support of shape (n_ballots,).

    Raises:
        ValueError: There are no ranking positions or array shapes cannot be broadcast together.
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


def number_of_voters(profile: RankProfile, *args: object, **kwargs: object) -> float:
    """Sum ballot weights, including fractional weights, in a ranked profile.

    Args:
        profile (RankProfile): Preference profile containing a Weight column.
        *args (object): Ignored positional arguments for the metric-call interface.
        **kwargs (object): Ignored keyword arguments for the metric-call interface.

    Returns:
        float: Total ballot weight.
    """
    del args, kwargs  # unused
    return float(profile.df["Weight"].sum())


# =================================================================================================
#                                            SIGMA UM
# =================================================================================================


def __asin_interpolation(misalignment: float) -> float:
    """Apply the arcsine UM transformation, saturating at one for support of at least 0.5.

    Args:
        misalignment (float): Nonnegative pairwise support value before interpolation.

    Returns:
        float: Interpolated score in [0, 1].

    Raises:
        ValueError: The support value is negative and has no real square root.
    """
    return float((2 / pi) * asin(sqrt(2 * misalignment)) if misalignment < 1 / 2 else 1)


def __odds_interpolation(misalignment: float) -> float:
    """Apply the odds UM transformation, saturating at one for support of at least 0.5.

    Args:
        misalignment (float): Nonnegative pairwise support value before interpolation.

    Returns:
        float: Interpolated score in [0, 1].
    """
    return float(misalignment / (1 - misalignment) if misalignment < 1 / 2 else 1)


def __linear_interpolation(misalignment: float) -> float:
    """Apply the linear UM transformation, saturating at one for support of at least 0.5.

    Args:
        misalignment (float): Nonnegative pairwise support value before interpolation.

    Returns:
        float: Interpolated score in [0, 1].
    """
    return float(2 * misalignment if misalignment < 1 / 2 else 1)


def _interpolation_function(interpolation_type: InterpolationType) -> Callable[[float], float]:
    """Select the scalar transformation used for a UM pairwise support value.

    Args:
        interpolation_type (InterpolationType): One of 'asin', 'odds', or 'linear'.

    Returns:
        Callable[[float], float]: Transformation saturating at one for support of at least 0.5.

    Raises:
        ValueError: The interpolation name is unsupported.
    """
    match interpolation_type:
        case "linear":
            return __linear_interpolation
        case "asin":
            return __asin_interpolation
        case "odds":
            return __odds_interpolation
        case _:
            raise ValueError(
                f"Unknown interpolation_type: {interpolation_type}. Must be 'asin', 'odds',"
                f" or 'linear'."
            )


def sigma_UM(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: MetricVariant = "worst_case",
    interpolation_type: InterpolationType = "asin",
) -> float:
    """Compute UM support for every ordered candidate pair in the election ranking.

    Lexicographically resolve tied ranks before comparing each higher-ranked candidate with
    each lower-ranked candidate. The average variant averages interpolated
    pairwise support; worst_case interpolates the minimum support.
    See https://arxiv.org/pdf/2506.12961 for the metric definition.

    Args:
        profile (RankProfile): Ranked ballots with positive total weight and at least two
            candidates.
        voting_rule (ElectionConstructor): Constructor accepting profile and m and returning an
            election ranking.
        n_seats (int): Number of seats; must be supported by the voting rule.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'worst_case'.
        interpolation_type (InterpolationType, optional): 'asin', 'odds', or 'linear'. Defaults to
            'asin'.

    Returns:
        float: UM score in [0, 1]; one means every tested pair has normalized support
            of at least 0.5.

    Raises:
        ValueError: The variant or interpolation is unsupported, the profile has no positive
            ranking length, or the voting rule rejects the election parameters.
        ZeroDivisionError: The election ranking contains fewer than two candidates.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    interpolation_fn = _interpolation_function(interpolation_type)

    raw_ranking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(raw_ranking)

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    max_ballot_len = profile.max_ranking_length
    if not isinstance(max_ballot_len, int) or max_ballot_len < 1:
        raise ValueError(
            f"Invalid max_ranking_length: {max_ballot_len}. Must be a positive integer."
        )
    ranking_array = profile.df[[f"Ranking_{i}" for i in range(1, max_ballot_len + 1)]].to_numpy()

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
    variant: MetricVariant = "worst_case",
    interpolation_type: InterpolationType = "asin",
) -> float:
    """Compute UM support for every elected-versus-unelected candidate pair.

    The winner set is the first n_seats candidates after lexicographic resolution of tied
    ranks. Compare each winner with each loser. The average variant averages interpolated
    pairwise support; worst_case interpolates the minimum support.
    See https://arxiv.org/pdf/2506.12961 for the metric definition.

    Args:
        profile (RankProfile): Ranked ballots with positive total weight and at least two
            candidates.
        voting_rule (ElectionConstructor): Constructor accepting profile and m and returning an
            election ranking.
        n_seats (int): Number of seats; must leave at least one winner and one loser.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'worst_case'.
        interpolation_type (InterpolationType, optional): 'asin', 'odds', or 'linear'. Defaults to
            'asin'.

    Returns:
        float: UM score in [0, 1]; one means every tested pair has normalized support
            of at least 0.5.

    Raises:
        ValueError: The variant or interpolation is unsupported, the profile has no positive
            ranking length, or the voting rule rejects the election parameters.
        ZeroDivisionError: The elected or unelected candidate group is empty.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    interpolation_fn = _interpolation_function(interpolation_type)

    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(
        voting_rule(profile=profile, m=n_seats).get_ranking()
    )

    weight_vector = profile.df["Weight"].to_numpy()
    n_voters = weight_vector.sum()

    max_ballot_len = profile.max_ranking_length
    if not isinstance(max_ballot_len, int) or max_ballot_len < 1:
        raise ValueError(
            f"Invalid max_ranking_length: {max_ballot_len}. Must be a positive integer."
        )
    ranking_array = profile.df[[f"Ranking_{i}" for i in range(1, max_ballot_len + 1)]].to_numpy()

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

    average_misalignment = total_alignment / (n_seats * (len(original_ranking) - n_seats))

    return average_misalignment if variant == "average" else interpolation_fn(misalignment)


# =================================================================================================
#                                            SIGMA IIA
# =================================================================================================


def sigma_IIA(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: MetricVariant = "average",
) -> float:
    """Compute ranking IIA under single-candidate removals.

    Remove each candidate in turn and compare the new election ranking with the original ranking
    restricted to the remaining candidates. Normalize Kendall distance by the number of remaining
    candidate pairs, then average over removals or take the largest distance for worst_case.
    Tied ranks are resolved lexicographically. See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): Ranked profile with at least three candidates.
        voting_rule (ElectionConstructor): Election constructor usable on the original and reduced
            profiles, accepting profile and m.
        n_seats (int): Number of seats, retained for each reduced election.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: One minus the aggregated normalized distance, in [0, 1]; one means no ranking change.

    Raises:
        ValueError: The variant is unsupported or a voting rule rejects a reduced election.
        AssertionError: Original and recomputed restricted rankings have different lengths.
        KeyError: A recomputed ranking omits a candidate from the original restricted ranking.
        ZeroDivisionError: Too few candidates remain to normalize a pairwise distance.
    """

    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    n_candidates = len(profile.candidates)
    ranking_before_unpacking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(ranking_before_unpacking)
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
            kendall_tau_distance(original_ranking_without_cand, voting_ranking_without_cand)
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
    variant: MetricVariant = "average",
) -> float:
    """Compute ranking IIA under all nontrivial subset removals.

    Remove each nonempty candidate subset that leaves at least two candidates, and compare the
    new ranking with the original ranking restricted to those candidates. Reduce the seat count
    to the number of remaining candidates when necessary. Average normalized Kendall distances
    equally across the tested subsets, or use the largest distance for worst_case.
    Tied ranks are resolved lexicographically. See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): Ranked profile with at least three candidates.
        voting_rule (ElectionConstructor): Election constructor usable on the original and reduced
            profiles, accepting profile and m.
        n_seats (int): Number of seats before capping for each reduced profile.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: One minus the aggregated normalized distance, in [0, 1]; one means no ranking change.

    Raises:
        ValueError: The variant is unsupported or a voting rule rejects a reduced election.
        AssertionError: Original and recomputed restricted rankings have different lengths.
        KeyError: A recomputed ranking omits a candidate from the original restricted ranking.
        ZeroDivisionError: Too few candidates remain to normalize the average over subsets.
    """

    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    n_candidates = len(profile.candidates)
    ranking_before_unpacking = voting_rule(profile=profile, m=n_seats).get_ranking()
    original_ranking = __unpack_ranking_with_lexicographic_tiebreak(ranking_before_unpacking)
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
                kendall_tau_distance(original_ranking_without_cand, voting_ranking_without_cand)
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
    variant: MetricVariant = "average",
) -> float:
    """Compute winner-set IIA under single-candidate removals.

    Remove candidates one at a time, excluding removal of the sole winner in a single-seat election.
    Reduce the seat count by the number of removed winners. Each comparison measures the fraction
    of available seats filled by retained original winners; aggregate by mean or minimum.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): Ranked profile on which to compare elected candidate sets.
        voting_rule (ElectionConstructor): Constructor accepting profile and m for each election.
        n_seats (int): Positive number of seats, at most the original candidate count.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: Winner retention in [0, 1]. Returns one when all candidates are elected or when
            a two-candidate election fills one seat.

    Raises:
        ValueError: The variant or seat count is unsupported, or a voting rule rejects an election.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    n_candidates = len(profile.candidates)
    if n_candidates == n_seats:
        return 1.0

    if n_candidates == 2 and n_seats == 1:
        return 1.0

    if n_seats < 1:
        raise ValueError(f"Number of seats must be at least 1, found {n_seats}.")
    if n_seats > n_candidates:
        raise ValueError(
            f"Number of seats must be at most the number of candidates, found {n_seats} seats"
            f" and {n_candidates} candidates."
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
        new_available_seats = n_seats - len(singleton.intersection(original_winners_set))

        new_winner_set = __unpack_ranking_with_lexicographic_tiebreak(
            voting_rule(
                remove_and_condense_rank_profile(candidate, profile),
                m=new_available_seats,
            ).get_elected()
        )
        new_dist = len(original_winners_set.intersection(new_winner_set)) / new_available_seats

        total_distance += new_dist
        smallest_normalized_intersection = min(smallest_normalized_intersection, new_dist)

    if variant == "worst_case":
        return smallest_normalized_intersection

    n_subsets_considered = len(profile.candidates) - (1 if len(original_winners_set) == 1 else 0)

    return total_distance / n_subsets_considered


def sigma_IIA_winner_set_all_subset(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: MetricVariant = "average",
) -> float:
    """Compute winner-set IIA under candidate-subset removals.

    Consider nonempty removal subsets except those containing every original winner and the subset
    containing exactly all original losers.
    Reduce the seat count by the number of removed winners. Each comparison measures the fraction
    of available seats filled by retained original winners; aggregate by mean or minimum.
    See https://arxiv.org/pdf/2506.12961 for details.

    Args:
        profile (RankProfile): Ranked profile on which to compare elected candidate sets.
        voting_rule (ElectionConstructor): Constructor accepting profile and m for each election.
        n_seats (int): Positive number of seats, at most the original candidate count.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: Winner retention in [0, 1]. Returns one when all candidates are elected or when
            a two-candidate election fills one seat.

    Raises:
        ValueError: The variant or seat count is unsupported, or a voting rule rejects an election.
    """
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

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
            f"Number of seats must be at most the number of candidates, found {n_seats} seats"
            f" and {n_candidates} candidates."
        )

    total_distance = 0
    smallest_normalized_intersection = 1

    # NOTE: Don't need to consider the whole set because we want for W \nsubseteq S
    # and the whole set will always contain W.
    for i in range(1, n_candidates):
        for candidate_subset in combinations(profile.candidates, i):
            candidate_subset_set = set(frozenset({cand}) for cand in candidate_subset)

            if original_winners_set.issubset(candidate_subset_set) or candidate_subset_set == (
                full_candidate_set - original_winners_set
            ):
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

            new_dist = len(original_winners_set.intersection(new_winner_set)) / new_available_seats

            total_distance += new_dist
            smallest_normalized_intersection = min(smallest_normalized_intersection, new_dist)

    if variant == "worst_case":
        return smallest_normalized_intersection

    n_subsets_considered = 2**n_candidates - 2 ** (n_candidates - n_seats) - 2

    return total_distance / n_subsets_considered


def __random_profile_ranking(
    profile: RankProfile, n_seats: int, excluded: Iterable[str] = ()
) -> tuple[frozenset[str], ...]:
    """Draw a random candidate ranking after excluding the supplied candidates.

    Candidates receiving votes precede uncast candidates, with each group shuffled separately
    using Python's random state. The requested seat count is validated against the remaining
    cast candidates, but the returned ranking includes all remaining candidates.

    Args:
        profile (RankProfile): Profile supplying cast and uncast candidate names.
        n_seats (int): Positive number of seats to fill with cast candidates.
        excluded (Iterable[str], optional): Candidates omitted from the ranking. Defaults to ().

    Returns:
        tuple[frozenset[str], ...]: Ordered singleton candidate sets.

    Raises:
        ValueError: The seat count is nonpositive or exceeds the remaining cast candidates.
    """
    excluded = set(excluded)
    remaining_cast = [
        candidate for candidate in profile.candidates_cast if candidate not in excluded
    ]
    if n_seats <= 0:
        raise ValueError("m must be strictly positive")
    if len(remaining_cast) < n_seats:
        raise ValueError("Not enough candidates received votes to be elected.")
    return tuple(frozenset({candidate}) for candidate in random_candidate_order(profile, excluded))


def sigma_IIA_random(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: MetricVariant = "average",
) -> float:
    """Compute single-removal ranking IIA using independent random candidate orderings.

    Draw the original and reduced rankings directly, with cast candidates before uncast candidates.
    This avoids constructing election states and uses Python's random state.

    Args:
        profile (RankProfile): Ranked profile with at least three candidates.
        voting_rule (ElectionConstructor): Ignored; retained for the common metric-call interface.
        n_seats (int): Positive seat count supported by the cast candidates after every removal.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: One minus the mean or largest normalized Kendall distance, in [0, 1].

    Raises:
        ValueError: The variant is unsupported or a random election cannot fill the requested seats.
        ZeroDivisionError: Fewer than two candidates remain for a normalized distance.
    """
    del voting_rule
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    n_candidates = len(profile.candidates)
    original_ranking = __random_profile_ranking(profile, n_seats)
    distance_divisor = comb(n_candidates - 1, 2)
    total_distance = 0
    largest_distance = 0

    for candidate in profile.candidates:
        original_ranking_without_cand = [
            c_set for c_set in original_ranking if candidate not in c_set
        ]
        new_ranking = __random_profile_ranking(profile, n_seats, (candidate,))
        distance = (
            kendall_tau_distance(original_ranking_without_cand, new_ranking) / distance_divisor
        )
        total_distance += distance
        largest_distance = max(largest_distance, distance)

    if variant == "worst_case":
        return 1 - largest_distance
    return 1 - total_distance / n_candidates


def sigma_IIA_winner_set_random(
    profile: RankProfile,
    voting_rule: ElectionConstructor,
    n_seats: int,
    *,
    variant: MetricVariant = "average",
) -> float:
    """Compute single-removal winner-set IIA from independent random candidate orderings.

    Skip removal of a sole winner and reduce the seat count when an original winner is removed.
    Cast candidates precede uncast candidates in each draw, using Python's random state.

    Args:
        profile (RankProfile): Ranked profile supplying candidates for each random election.
        voting_rule (ElectionConstructor): Ignored; retained for the common metric-call interface.
        n_seats (int): Positive number of seats, supported by the remaining cast candidates.
        variant (MetricVariant, optional): 'average' or 'worst_case'. Defaults to 'average'.

    Returns:
        float: Mean or minimum fraction of available seats retaining original winners. Returns one
            when all candidates are elected or a two-candidate election fills one seat.

    Raises:
        ValueError: The variant is unsupported or a random election cannot fill the requested seats.
    """
    del voting_rule
    if variant not in ("average", "worst_case"):
        raise ValueError(f"Unknown variant: {variant}. Must be 'average' or 'worst_case'.")

    n_candidates = len(profile.candidates)
    original_winners_set = set(__random_profile_ranking(profile, n_seats)[:n_seats])
    if n_candidates == n_seats or (n_candidates == 2 and n_seats == 1):
        return 1.0
    if n_seats < 1:
        raise ValueError(f"Number of seats must be at least 1, found {n_seats}.")
    if n_seats > n_candidates:
        raise ValueError(
            "Number of seats must be at most the number of candidates, "
            f"found {n_seats} seats and {n_candidates} candidates."
        )

    total_distance = 0
    smallest_normalized_intersection = 1
    for candidate in profile.candidates:
        singleton = {frozenset({candidate})}
        if singleton == original_winners_set:
            continue

        new_available_seats = n_seats - len(singleton.intersection(original_winners_set))
        new_winner_set = set(
            __random_profile_ranking(profile, new_available_seats, (candidate,))[
                :new_available_seats
            ]
        )
        distance = len(original_winners_set.intersection(new_winner_set)) / (new_available_seats)
        total_distance += distance
        smallest_normalized_intersection = min(smallest_normalized_intersection, distance)

    if variant == "worst_case":
        return smallest_normalized_intersection
    n_subsets_considered = len(profile.candidates) - (1 if len(original_winners_set) == 1 else 0)
    return total_distance / n_subsets_considered
