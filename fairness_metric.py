#This script contains the fairness metric functions of IIA and UF

#first we define the kendall tau distace function

def kendall_tau_distance(list1, list2):
    """
    Compute Kendall Tau distance between two rankings (lists).
    
    Args:
        list1 (list): First ranking (ordered list of candidates).
        list2 (list): Second ranking (ordered list of candidates).
    
    Returns:
        int: Kendall Tau distance (number of pairwise disagreements).
    """
    assert len(list1) == len(list2), "Lists must have the same size"
    
    distance = 0
    n = len(list1)
    
    # Build position maps for fast lookup
    pos1 = {candidate: idx for idx, candidate in enumerate(list1)}
    pos2 = {candidate: idx for idx, candidate in enumerate(list2)}
    
    # Check all pairs
    for i in range(n):
        for j in range(i+1, n):
            cand_i = list1[i]
            cand_j = list1[j]
            
            # Compare relative order
            if (pos1[cand_i] - pos1[cand_j]) * (pos2[cand_i] - pos2[cand_j]) < 0:
                # They disagree
                distance += 1
    
    return distance

from votekit.cleaning import remove_noncands

def sigma_IIA(profile, voting_rule):
    """
    Compute σIIA fairness score for a given voting rule and profile.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.
        voting_rule (function): A function like Ranked_Borda(profile) or Ranked_Plurality(profile).
    
    Returns:
        float: σIIA score between 0 and 1.
    """
    original_ranking = voting_rule(profile)
    M = len(profile.candidates)
    total_distance = 0

    for candidate in profile.candidates:
        # compute profile without the candidate
        profile_without_candidate = remove_noncands(profile, [candidate])
        
        # Get rankings
        ranking_without_candidate = voting_rule(profile_without_candidate)
        original_ranking_without_candidate = [cand for cand in original_ranking if cand != candidate]
        
        # Compute Kendall Tau distance
        distance = kendall_tau_distance(ranking_without_candidate, original_ranking_without_candidate)
        
        total_distance += distance

    # Normalize and invert
    sigma_iia = 1 - total_distance / (M * (M-1)* (M-2)) / 2

    return sigma_iia
