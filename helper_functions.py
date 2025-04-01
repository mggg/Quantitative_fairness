#This files contains some helper functions
def flatten_ballot_ranking(ballot):
    """
    Convert a VoteKit ballot's ranking (stored as a tuple of frozensets)
    into a simple list (assumes each frozenset contains exactly one candidate).
    """
    return [next(iter(fs)) for fs in ballot.ranking]

