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
    sigma_iia = 1 - total_distance / ((M * (M-1)* (M-2)) / 2)

    return sigma_iia

#Sigma_UF metric

def sigma_UF(profile, voting_rule):
    """
    Compute Unanimity Fairness (σUF) for a given voting rule and profile.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.
        voting_rule (function): A function like Ranked_Borda(profile) or Ranked_Plurality(profile).
    
    Returns:
        float: σUF score between 0 and 1.
    """
    candidates = profile.candidates
    N = sum(ballot.weight for ballot in profile.ballots)  # Total voter weight

    # Get the full ranking from the voting rule
    ranking = voting_rule(profile)

    # Map candidates to positions
    rank_position = {cand: idx for idx, cand in enumerate(ranking)}

    min_ratio = 1.0  # Initialize

    # For every unordered candidate pair (A, B)
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            A = candidates[i]
            B = candidates[j]

            A_over_B = 0
            B_over_A = 0

            # Count support for A over B and B over A
            for ballot in profile.ballots:
                weight = ballot.weight
                if not ballot.ranking:
                    continue
                ranks = {cand: idx for idx, group in enumerate(ballot.ranking) for cand in group}

                A_in = A in ranks
                B_in = B in ranks

                if A_in and B_in:
                    if ranks[A] < ranks[B]:
                        A_over_B += weight
                    elif ranks[B] < ranks[A]:
                        B_over_A += weight
                elif A_in and not B_in:
                    A_over_B += weight
                elif B_in and not A_in:
                    B_over_A += weight
                else:  # neither A nor B ranked
                    A_over_B += 0.5 * weight
                    B_over_A += 0.5 * weight

            # Now normalize
            SA = A_over_B / N
            SB = B_over_A / N
            max_support = max(SA, SB)

            if max_support == 0:
                continue  # No information about A vs B

            # Depending on outcome ranking
            if rank_position[A] < rank_position[B]:  # A ranked above B
                ratio = SA / max_support
            else:  # B ranked above A
                ratio = SB / max_support

            # Update minimum ratio
            min_ratio = min(min_ratio, ratio)

    return min_ratio

