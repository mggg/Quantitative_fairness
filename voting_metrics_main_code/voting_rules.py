"""Construct the voting rules used by the replication metrics."""

import random
from collections.abc import Iterable
from functools import partial
from typing import Protocol

from votekit.elections import STV, Borda, Plurality, RankedPairs
from votekit.elections.election_state import ElectionState
from votekit.elections.election_types.ranking.abstract_ranking import RankingElection
from votekit.models import Election
from votekit.pref_profile import RankProfile

from voting_metrics_main_code.constants import AllowedRule


class ElectionConstructor(Protocol):
    """Common constructor arguments used when scoring an election."""

    def __call__(self, profile: RankProfile, *, m: int = 1) -> Election:
        """Run an election on a ranked profile for the requested number of seats.

        Args:
            profile (RankProfile): Ballots and candidates for the election.
            m (int, optional): Number of seats to elect. Defaults to 1.

        Returns:
            Election: Completed election exposing its ranking and elected candidates.
        """
        ...


def random_candidate_order(profile: RankProfile, excluded: Iterable[str] = ()) -> list[str]:
    """Shuffle cast and uncast candidates separately, placing cast candidates first.

    Both groups start in sorted order, so a seeded Python random state determines the result
    independently of set iteration order. Exclusions are applied before shuffling.

    Args:
        profile (RankProfile): Profile supplying candidate names and the subset receiving votes.
        excluded (Iterable[str], optional): Candidates omitted from both groups. Defaults to ().

    Returns:
        list[str]: All nonexcluded candidates, with each appearing once.
    """
    excluded = set(excluded)
    cast_cands = sorted(cand for cand in profile.candidates_cast if cand not in excluded)
    uncast_cands = sorted(set(profile.candidates) - set(profile.candidates_cast) - excluded)
    random.shuffle(cast_cands)
    random.shuffle(uncast_cands)
    return cast_cands + uncast_cands


class ElectRandom(RankingElection):
    """Elect a random subset of cast candidates and rank the remaining candidates.

    Rankings place cast candidates before uncast candidates, with each group shuffled separately.
    Construction runs the single-round election using Python's random state.

    Args:
        profile (RankProfile): Profile supplying candidate names and cast candidates.
        tiebreak (str, optional): Stored for API compatibility; does not affect the draw.
            Defaults to 'random'.
        m (int, optional): Number of cast candidates to elect. Defaults to 1.

    Raises:
        ValueError: m is nonpositive or exceeds the number of cast candidates.
    """

    def __init__(
        self,
        profile: RankProfile,
        tiebreak: str = "random",
        m: int = 1,
    ) -> None:
        """Run a one-round random election for the requested seat count.

        Args:
            profile (RankProfile): Profile supplying candidate names and cast candidates.
            tiebreak (str, optional): Stored but unused compatibility setting. Defaults to 'random'.
            m (int, optional): Number of cast candidates to elect. Defaults to 1.

        Raises:
            ValueError: m is nonpositive or exceeds the number of cast candidates.
        """
        if m <= 0:
            raise ValueError("m must be strictly positive")
        if len(profile.candidates_cast) < m:
            raise ValueError("Not enough candidates received votes to be elected.")

        self.m = m

        self.tiebreak = tiebreak

        super().__init__(
            profile,
            sort_high_low=True,
        )

    def _is_finished(self) -> bool:
        """Check whether the election state contains the requested number of winners.

        Returns:
            bool: True when exactly m candidates have been elected.
        """
        elected_cands = [c for s in self.get_elected() for c in s]

        return len(elected_cands) == self.m

    def _run_step(
        self,
        profile: RankProfile,
        prev_state: ElectionState,
        store_states: bool = False,
    ) -> RankProfile:
        """Draw one random ranking and optionally append its election state.

        Args:
            profile (RankProfile): Ballots and candidates used for this round's draw.
            prev_state (ElectionState): Previous state, supplying the round number.
            store_states (bool, optional): Append the elected and remaining candidates to
                election_states when True. Defaults to False.

        Returns:
            RankProfile: The unchanged input profile; ballots are not removed or reweighted.
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
    """Bind a voting rule's tie-breaking strategy and, for approval, its score vector.

    Approval rules use Borda with one point for each approved position and zero for later ones.
    The returned factory forwards arguments to the selected VoteKit rule; metrics use its common
    profile and m arguments. Election construction and validation happen when the factory is called.

    Args:
        n_cands (int): Candidate count used to size approval score vectors.
        voting_rule_name (AllowedRule): Supported rule name.
        tiebreak (str, optional): Strategy bound into the selected rule; ignored by ElectRandom.
            Defaults to 'lex'.

    Returns:
        ElectionConstructor: Callable running an election with the configured rule settings.

    Raises:
        ValueError: The rule name is unsupported or an approval rule requests more approved
            positions than n_cands.
    """

    if voting_rule_name in ("2-approval", "3-approval"):
        approval_count = 2 if voting_rule_name == "2-approval" else 3
        if n_cands < approval_count:
            raise ValueError(f"{voting_rule_name} requires at least {approval_count} candidates.")

        score_vector = [1] * approval_count + [0] * (n_cands - approval_count)
        return partial(Borda, tiebreak=tiebreak, score_vector=score_vector)

    rule_types = {
        "borda": Borda,
        "plurality": Plurality,
        "stv": STV,
        "ranked-pairs": RankedPairs,
        "random": ElectRandom,
    }
    if voting_rule_name not in rule_types:
        raise ValueError(f"Voting rule {voting_rule_name!r} not recognized.")

    return partial(rule_types[voting_rule_name], tiebreak=tiebreak)
