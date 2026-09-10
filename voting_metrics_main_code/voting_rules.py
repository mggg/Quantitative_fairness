import random
from collections.abc import Iterable
from typing import Any, Callable, TypeAlias

from votekit.elections import STV, Borda, Plurality, RankedPairs
from votekit.elections.election_state import ElectionState
from votekit.elections.election_types.ranking.abstract_ranking import RankingElection
from votekit.models import Election
from votekit.pref_profile import RankProfile

from voting_metrics_main_code.constants import AllowedRule

ElectionConstructor: TypeAlias = Callable[..., Election]


def random_candidate_order(profile: RankProfile, excluded: Iterable[str] = ()) -> list[str]:
    """Randomly order the profile's cast candidates, followed by its uncast candidates."""
    excluded = set(excluded)
    cast_cands = sorted(cand for cand in profile.candidates_cast if cand not in excluded)
    uncast_cands = sorted(set(profile.candidates) - set(profile.candidates_cast) - excluded)
    random.shuffle(cast_cands)
    random.shuffle(uncast_cands)
    return cast_cands + uncast_cands


class ElectRandom(RankingElection):
    """
    Randomly ranks all of the candidates that received votes and then elects the top m candidates.

    Args:
        profile (RankProfile): Profile to conduct election on.
        tiebreak (str, optional): Included for API compatibility; not used. Defaults to "random".
        m (int, optional): Number of seats to elect. Defaults to 1.
    """

    def __init__(
        self,
        profile: RankProfile,
        tiebreak: str = "random",
        m: int = 1,
    ) -> None:
        if m <= 0:
            raise ValueError("m must be strictly positive")
        if len(profile.candidates_cast) < m:
            raise ValueError("Not enough candidates received votes to be elected.")

        self.m = m

        # Not used
        self.tiebreak = tiebreak

        super().__init__(
            profile,
            sort_high_low=True,
        )

    def _is_finished(self) -> bool:
        """
        Check if the election is finished.

        Returns:
            bool: True if the required number of candidates have been elected.
        """
        # single round election
        elected_cands = [c for s in self.get_elected() for c in s]

        if len(elected_cands) == self.m:
            return True
        return False

    def _run_step(
        self,
        profile: RankProfile,
        prev_state: ElectionState,
        store_states: bool = False,
    ) -> RankProfile:
        """
        Run one step of an election from the given profile and previous state. Since this is
        a single-round election, this will complete the election and return the final profile.

        Args:
            profile (RankProfile): Profile of ballots.
            prev_state (ElectionState): The previous ElectionState.
            store_states (bool, optional): Included for compatibility with the base class but not
                used in this election type.

        Returns:
            RankProfile: The profile of ballots after the round is completed.
        """
        ordered_candidates = random_candidate_order(profile)

        elected = tuple(frozenset({c}) for c in ordered_candidates[: self.m])
        remaining = tuple(frozenset({c}) for c in ordered_candidates[self.m :])

        if store_states:
            new_state = ElectionState(
                round_number=prev_state.round_number + 1,
                elected=elected,
                remaining=remaining,
            )

            self.election_states.append(new_state)

        return profile


def build_voting_rule(
    n_cands: int, voting_rule_name: AllowedRule, tiebreak: str = "lex"
) -> ElectionConstructor:
    """
    Build a voting rule constructor based on a name and candidate count.

    Args:
        n_cands (int): Number of candidates.
        voting_rule_name (AllowedRule): Name of the voting rule to build.
        tiebreak (str, optional): Tiebreak strategy passed to the rule. Defaults to "lex".

    Returns:
        ElectionConstructor: A callable that constructs the requested election rule.
    """

    match voting_rule_name:
        case "borda":

            def factory(*args: Any, **kwargs: Any) -> Election:
                return Borda(*args, tiebreak=tiebreak, **kwargs)

        case "3-approval":
            if n_cands < 3:
                raise ValueError("3-approval requires at least 3 candidates.")
            sv = [1] * 3 + [0] * (n_cands - 3)

            def factory(*args: Any, **kwargs: Any) -> Election:
                return Borda(*args, tiebreak=tiebreak, score_vector=sv, **kwargs)

        case "2-approval":
            if n_cands < 2:
                raise ValueError("2-approval requires at least 2 candidates.")
            sv = [1] * 2 + [0] * (n_cands - 2)

            def factory(*args: Any, **kwargs: Any) -> Election:
                return Borda(*args, tiebreak=tiebreak, score_vector=sv, **kwargs)

        case "plurality":

            def factory(*args: Any, **kwargs: Any) -> Election:
                return Plurality(*args, tiebreak=tiebreak, **kwargs)

        case "stv":

            def factory(*args: Any, **kwargs: Any) -> Election:
                return STV(*args, tiebreak=tiebreak, **kwargs)

        case "ranked-pairs":

            def factory(*args: Any, **kwargs: Any) -> Election:
                return RankedPairs(*args, tiebreak=tiebreak, **kwargs)

        case "random":

            def factory(*args: Any, **kwargs: Any) -> Election:
                return ElectRandom(*args, tiebreak=tiebreak, **kwargs)

        case _:
            raise ValueError(f"Voting rule {voting_rule_name!r} not recognized.")

    return factory
