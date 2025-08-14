from typing import Callable, Literal, TypeAlias
from votekit.elections import Borda, STV, Plurality, Election

ElectionConstructor: TypeAlias = Callable[..., Election]
AllowedRule = Literal["borda", "3-approval", "2-approval", "plurality", "stv"]


def build_voting_rule(
    n_cands: int, voting_rule_name: AllowedRule
) -> ElectionConstructor:
    if voting_rule_name == "borda":

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak="first_place", **kwargs)

        return factory

    elif voting_rule_name == "3-approval":
        if n_cands < 3:
            raise ValueError("3-approval requires at least 3 candidates.")
        sv = [1] * 3 + [0] * (n_cands - 3)

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak="first_place", score_vector=sv, **kwargs)

        return factory

    elif voting_rule_name == "2-approval":
        if n_cands < 2:
            raise ValueError("2-approval requires at least 2 candidates.")
        sv = [1] * 2 + [0] * (n_cands - 2)

        def factory(*args, **kwargs) -> Election:
            return Borda(*args, tiebreak="first_place", score_vector=sv, **kwargs)

        return factory

    elif voting_rule_name == "plurality":

        def factory(*args, **kwargs) -> Election:
            return Plurality(*args, tiebreak="borda", **kwargs)

        return factory

    elif voting_rule_name == "stv":

        def factory(*args, **kwargs) -> Election:
            return STV(*args, tiebreak="borda", **kwargs)

        return factory

    else:
        raise ValueError(f"Voting rule {voting_rule_name!r} not recognized.")
