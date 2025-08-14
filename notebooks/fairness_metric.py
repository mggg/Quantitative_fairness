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

from votekit.cleaning import remove_and_condense

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
        profile_without_candidate = remove_and_condense([candidate], profile)
        
        # Get rankings
        ranking_without_candidate = voting_rule(profile_without_candidate)
        original_ranking_without_candidate = [cand for cand in original_ranking if cand != candidate]
        
        # Compute Kendall Tau distance
        distance = kendall_tau_distance(ranking_without_candidate, original_ranking_without_candidate)
        
        total_distance += distance

    # Normalize and invert
    sigma_iia = 1 - total_distance / ((M * (M-1)* (M-2)) / 2)

    return sigma_iia

#Sigma_UM metric

def sigma_UM(profile, voting_rule):
    """
    Compute Unanimity Fairness (σUM) for a given voting rule and profile.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.
        voting_rule (function): A function like Ranked_Borda(profile) or Ranked_Plurality(profile).
    
    Returns:
        float: σUM score between 0 and 1.
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

            min_majority = min_ratio / (min_ratio + 1)

    return (2/np.pi)*(np.arcsin(np.sqrt(2*min_majority)))



#We define a separate function for computing the IIA metric specifically for STV elections on the Scottish dataset.
#This is necessary because the number of seats varies across elections, and we want to treat the number of seats as an additional parameter.


def sigma_IIA_STV(profile, seats, voting_rule):
    """
    Compute σIIA fairness score for a given a STV, profile and seats.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.
        voting_rule (function): A STV voting rule function that takes a profile,seats and returns a ranking.
    Returns:
        float: σIIA score between 0 and 1.
    """
    original_ranking = voting_rule(profile,seats)
    M = len(profile.candidates)
    total_distance = 0

    for candidate in profile.candidates:
        # compute profile without the candidate
        profile_without_candidate = remove_and_condense(profile, [candidate])
        
        # Get rankings
        ranking_without_candidate = voting_rule(profile_without_candidate,seats)
        original_ranking_without_candidate = [cand for cand in original_ranking if cand != candidate]
        
        # Compute Kendall Tau distance
        distance = kendall_tau_distance(ranking_without_candidate, original_ranking_without_candidate)
        
        total_distance += distance

    # Normalize and invert
    sigma_iia = 1 - total_distance / ((M * (M-1)* (M-2)) / 2)

    return sigma_iia


def sigma_UF_STV(profile,seats, voting_rule):
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
    ranking = voting_rule(profile, seats)

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

            min_majority = min_ratio / (min_ratio + 1)

    return (2/np.pi)*(np.arcsin(np.sqrt(2*min_majority)))

  

#Functions made based on Votekit version 3.2.1
from votekit.cleaning import remove_and_condense


#-------- WINNER SET RULES--------------

#IIA metric

def sigma_IIA_winner(profile, voting_rule, seats):
    """
    Compute σIIA fairness score for a given voting rule and profile,
    focusing on the winner set.

    Args:
        profile (PreferenceProfile): The input profile with ballots and candidates.
        voting_rule (function): A function like Ranked_Borda(profile) or Ranked_Plurality(profile).
        seats (int): Number of winners to select.
    
    Returns:
        float: σIIA score between 0 and 1.
    """
    winners = voting_rule(profile, m=seats, tiebreak = 'random').get_elected()
    winner_set = set([next(iter(w)) for w in winners])  # assumes winners is a list of singleton sets/lists

    M = len(winner_set)
    total_distance = 0

    for cand in profile.candidates:
        if cand in winner_set and M > 1:
            winner_set_without_cand = winner_set - {cand}

            new_profile = remove_and_condense([cand], profile)
            new_winners = voting_rule(new_profile, m=seats - 1,tiebreak = 'random').get_elected()
            new_winners_set = set([next(iter(w)) for w in new_winners])

            
            total_distance += len(winner_set_without_cand & new_winners_set) / (M - 1)
            
        else:
            new_profile = remove_and_condense([cand], profile)
            new_winners = voting_rule(new_profile, m=seats, tiebreak = 'random').get_elected()
            new_winners_set = set([next(iter(w)) for w in new_winners])

            total_distance += len(winner_set & new_winners_set) / M

    return total_distance / len(profile.candidates)


#UM netric


import numpy as np
#Below is winner set version for the UM Metric

def sigma_UM_winner_set(profile, voting_rule, seats):
    """
    Compute the UM (unanimity majority) score for a voting rule that outputs a winner set of size equal to seats.

    Args:
        profile (PreferenceProfile): The voter profile.
        voting_rule (callable): A function or class that takes (profile, seats) and returns an election object with get_elected().
        seats (int): Number of winners to be selected.

    Returns:
        float: UM fairness score between 0 and 1.
    """
    #Run the voting rule to get the election result

  
    
    election = voting_rule(profile , seats)
    
    #Extract winners from the election
    #Handles tuple of frozensets like (frozenset({'A'}), frozenset({'B'}), ...)
    winners_raw = election.get_elected()
    winners = [next(iter(group)) for group in winners_raw]  # flatten frozensets
    winners_set = set(winners)

    #  Compute σ_UM based on winner vs loser support
    candidates = profile.candidates
    N = sum(ballot.weight for ballot in profile.ballots)

    min_majority = 1.0 

    for A in winners_set:
        for B in candidates:
            if B in winners_set or A == B:
                continue  # Only compare A ∈ winners, B ∉ winners

            A_over_B = 0

            for ballot in profile.ballots:
                weight = ballot.weight
                if not ballot.ranking:
                    continue

                # Build rank map: {candidate: rank index}
                ranks = {cand: idx for idx, group in enumerate(ballot.ranking) for cand in group}
                A_in = A in ranks
                B_in = B in ranks

                if A_in and B_in:
                    if ranks[A] < ranks[B]:
                        A_over_B += weight
                elif A_in and not B_in:
                    A_over_B += weight
                elif not A_in and not B_in:
                    A_over_B += 0.5 * weight

            support = A_over_B / N
            min_majority = min(min_majority, support)

    #  Apply the UM formula
    #min_majority is the misalignment score
    return 1.0 if min_majority >= 0.5 else (2/np.pi)*(np.arcsin(np.sqrt(2*min_majority)))





