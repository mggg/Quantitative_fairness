#This is the voting_rules script made for the modified voting rules (outputting the complete ranking)

#Make sure votekit is installed
#if not installed, run the following command:
#pip install votekit
# All the voting rules below are for complete rankings output

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

# Ranked_STV method for complete ranking designed specifically for Scottish STV elections

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


#STV method used for Simluation, here you can change the number of seats from 3 to any other number accordingly
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

#IRV rule

def Ranked_1_STV(profile):
    """
    Given a PreferenceProfile, returns the complete STV ranking as a list.
    Note thet this is a STV method with 3 seats.
    
    Args:
        profile (PreferenceProfile): The preference profile with ballots and candidates.
    
    Returns:
        list: Candidates ranked from winner to last place according to votekit implementation of STV.
    """

    election = STV (profile, m= 1)
    
    # Get the full ranking (tuple of frozensets)
    borda_ranking = election.get_ranking(-1)
    
    # Flatten the frozensets into a list
    ranking_list = []
    for group in borda_ranking:
        ranking_list.extend(list(group))  # groups can have ties (more than one candidate)
    
    return ranking_list

## Sigma_UM optimal voting rule

import networkx as nx
from votekit.graphs import PairwiseComparisonGraph

def Optimal_sigma_UM_voting_rule_ranking(profile):
    """
    Compute the σUF-optimal ranking for a given profile by iteratively removing
    minimum-weight edges until a topological sort is possible.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.

    Returns:
        list: A topological ordering (ranking) of candidates minimizing σUF.
    """
    PWCG = PairwiseComparisonGraph(profile)
    G = PWCG.pairwise_graph.copy()  # Make a copy to avoid modifying original

    try:
        # Try initial topological sort
        topo_gen = nx.all_topological_sorts(G)
        T = next(topo_gen)
        return T
    except nx.NetworkXUnfeasible:
        pass  # Continue to iterative edge removal

    while True:
        # Find the minimum edge weight
        min_weight = min(data['weight'] for _, _, data in G.edges(data=True))

        # Find and remove all edges with that minimum weight
        edges_to_remove = [(u, v) for u, v, data in G.edges(data=True) if data['weight'] == min_weight]
        G.remove_edges_from(edges_to_remove)

        try:
            topo_gen = nx.all_topological_sorts(G)
            T = next(topo_gen)
            return T  # Return the first valid topological sort
        except nx.NetworkXUnfeasible:
            continue  # Keep removing edges




