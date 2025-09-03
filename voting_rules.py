from typing import Callable, Literal, TypeAlias
from votekit.elections import Borda, STV, Plurality, RankedPairs
from votekit.models import Election

ElectionConstructor: TypeAlias = Callable[..., Election]
AllowedRule: TypeAlias = Literal[
    "borda", "3-approval", "2-approval", "plurality", "stv", "ranked-pairs"
]


def build_voting_rule(
    n_cands: int, voting_rule_name: AllowedRule, tiebreak: str = "lex"
) -> ElectionConstructor:
    if voting_rule_name == "borda":

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak=tiebreak, **kwargs)

        return factory

    elif voting_rule_name == "3-approval":
        if n_cands < 3:
            raise ValueError("3-approval requires at least 3 candidates.")
        sv = [1] * 3 + [0] * (n_cands - 3)

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak=tiebreak, score_vector=sv, **kwargs)

        return factory

    elif voting_rule_name == "2-approval":
        if n_cands < 2:
            raise ValueError("2-approval requires at least 2 candidates.")
        sv = [1] * 2 + [0] * (n_cands - 2)

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak=tiebreak, score_vector=sv, **kwargs)

        return factory

    elif voting_rule_name == "plurality":

        def factory(*args, **kwargs) -> Election:
            return Plurality(*args, tiebreak=tiebreak, **kwargs)

        return factory

    elif voting_rule_name == "stv":

        def factory(*args, **kwargs) -> Election:
            return STV(*args, tiebreak=tiebreak, **kwargs)

        return factory

    elif voting_rule_name == "ranked-pairs":

        def factory(*args, **kwargs) -> Election:
            return RankedPairs(*args, tiebreak=tiebreak, **kwargs)

        return factory

    else:
        raise ValueError(f"Voting rule {voting_rule_name!r} not recognized.")
