#This is the voting_rules script made for havng the modified voting rules

#Make sure votekit is installed

from votekit.elections import Borda, Plurality


def Ranked_Borda(profile):
    """
    Given a PreferenceProfile, returns the complete Borda ranking as a list.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to Borda scores.
    """

    election = Borda(profile, m= len(profile.candidates))
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list

def Ranked_Plurality(profile):
    """
    Given a PreferenceProfile, returns the complete Borda ranking as a list.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to Borda scores.
    """

    election = Plurality(profile, m= len(profile.candidates))
    
    # Get the full ranking (tuple of frozensets)
    plurality_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in plurality_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list


