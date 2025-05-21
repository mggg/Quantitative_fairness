#This is the voting_rules script made for the modified voting rules (outputting the complete ranking)

#Make sure votekit is installed
#if not installed, run the following command:
#pip install votekit

from votekit.elections import Borda, Plurality, STV


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
        list: Candidates ranked from winner to last place according to Plurality scores (1,0,...0).
    """

    election = Plurality(profile, m= len(profile.candidates))
    
    # Get the full ranking (tuple of frozensets)
    plurality_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in plurality_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list

def Ranked_2_Approval(profile):
    """
    Given a PreferenceProfile, returns the complete 2-approval ranking as a list.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to (1,1,0,...,0).
    """
   
    M = len(profile.candidates)
    
    # Construct the 2-approval score vector: 1 for top 2, 0 for others
    approval_vector = [1 if i < 2 else 0 for i in range(M)]

    election = Borda(profile, m= len(profile.candidates), score_vector = approval_vector)
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list

def Ranked_3_Approval(profile):
    """
    Given a PreferenceProfile, returns the complete 3-approval ranking as a list.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to (1,1,1,0,..,0).
    """
   
    M = len(profile.candidates)
    
    # Construct the 3-approval score vector: 1 for top 3, 0 for others
    approval_vector = [1 if i < 3 else 0 for i in range(M)]

    election = Borda(profile, m= len(profile.candidates), score_vector = approval_vector)
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list


def Ranked_STV(profile, seats):
    """
    Given a PreferenceProfile (scottish profile), and seats returns the complete STV ranking as a list.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to votekit ranking implementation of STV.
    """

    election = STV (profile, m= seats)
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list


#STV method used for Simluation
def Ranked_3_STV(profile):
    """
    Given a PreferenceProfile, returns the complete STV ranking as a list.
    Note thet this is a STV method with 3 seats.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to votekit implementation of STV.
    """

    election = STV (profile, m= 3)
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list




