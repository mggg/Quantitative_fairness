from votekit.pref_profile import RankProfile
from votekit.utils import score_dict_from_score_vector
from votekit.elections import FastSTV as STV
from votekit.elections import RankedPairs
import pandas as pd

ROUND = 4
score_vectors = {
    "fpv": (1, 0, 0, 0, 0, 0),
    "top3": (1, 1, 1, 0, 0, 0),
    "top3borda": (3, 2, 1, 0, 0, 0),
    "borda": (6, 5, 4, 3, 2, 1),
}

elections = {"STV": STV, "RankedPairs": RankedPairs}

slates = {
    "D1": [
        ["Steph Routh", "Timur Ender", "Candace Avalos", "Jamie Dunphy"],
        ["Terrence Hayes", "Loretta Smith", "Noah Ernst"],
    ],
    "D2": [
        [
            "Jonathan Tasini",
            "Nat West",
            "Michelle DePass",
            "Marnie Glickman",
            "Sameer Kanal",
        ],
        ["Elana Pirtle-Guiney", "Tiffani Penson", "Dan Ryan", "Mariah Hudson"],
    ],
    "D3": [
        ["Jesse Cornett", "Steve Novick", "Rex Burkholder"],
        ["Angelita Morillo", "Tiffany Koyama Lane"],
    ],
    "D4": [
        ["Sarah Silkie", "Mitch Green", "Lisa Freeman", "Chad Lykins"],
        ["Olivia Clark", "Eric Zimmerman", "Eli Arnold", "Bob Weinstein"],
    ],
}

for district in range(1, 5):
    print(f"District {district}")
    profile = RankProfile.from_csv(f"../data/Portland_D{district}_cleaned_votekit.csv")
    slate_1 = slates[f"D{district}"][0]
    slate_2 = slates[f"D{district}"][1]
    election_seat_shares = {}
    for election_str, election in elections.items():
        election_obj = election(profile, m=3)
        winners = [c for c_set in election_obj.get_elected() for c in c_set]

        slate_1_seat_share = sum(1 for winner in winners if winner in slate_1) / 3
        election_seat_shares[election_str] = slate_1_seat_share
    print(f"Election seat shares of slate 1: {election_seat_shares}")
    columns = {
        "Slate 1 Support Share": [],
        # "Slate 2 Support Share": [],
    }
    columns.update({f"{election_str}_Disprop": [] for election_str in elections.keys()})

    for score_vec_str, score_vec in score_vectors.items():
        score_dict = score_dict_from_score_vector(profile, score_vec)

        slate_1_count = sum(score_dict[candidate] for candidate in slate_1)
        slate_2_count = sum(score_dict[candidate] for candidate in slate_2)

        slate_1_share = round(slate_1_count / (slate_1_count + slate_2_count), ROUND)
        # slate_2_share = round(slate_2_count / (slate_1_count + slate_2_count), ROUND)

        columns["Slate 1 Support Share"].append(slate_1_share)
        # columns["Slate 2 Support Share"].append(slate_2_share)
        for election_str in elections.keys():
            columns[f"{election_str}_Disprop"].append(
                round(
                    1 - abs(election_seat_shares[election_str] - slate_1_share), ROUND
                )
            )

    df = pd.DataFrame(columns)
    df.index = score_vectors.keys()
    print(f"Slate 1: {slate_1}")
    print(f"Slate 2: {slate_2}")
    print(df.to_string())
    df.to_csv(
        f"../data/Portland_D{district}_combined_support_for_slates.csv", index=True
    )
    print("--------------------------------\n")
