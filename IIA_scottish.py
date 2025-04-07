import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from math import floor
import os
# -------------------------
# CSV Parsing
# -------------------------
def parse_election_csv(filepath):
    with open(filepath, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]

    num_cands, num_seats = map(int, lines[0].split(',')[:2])
    cand_line_start = next(i for i, line in enumerate(lines) if line.startswith('"Candidate'))
    ballot_lines = lines[1:cand_line_start]

    ballots = []
    for line in ballot_lines:
        try:
            parts = [int(x) for x in line.strip(',').split(',') if x]
            count, ranking = parts[0], parts[1:]
            for _ in range(count):
                ballots.append(ranking)
        except:
            continue

    all_candidates = sorted(set(c for ballot in ballots for c in ballot))
    return ballots, all_candidates, num_seats

# -------------------------
# Different Voting rules (I didn't use votekit functions rather wrote the voting rules manually for now)
# -------------------------
def borda_ranking(ballots, candidates):
    scores = {c: 0 for c in candidates}
    max_rank = max(len(b) for b in ballots)
    for ballot in ballots:
        for i, c in enumerate(ballot):
            scores[c] += (max_rank - i)
    return [c for c, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]

def plurality_ranking(ballots, candidates):
    counts = Counter()
    for ballot in ballots:
        for c in ballot:
            if c in candidates:
                counts[c] += 1
                break
    for c in candidates:
        counts.setdefault(c, 0)
    return [c for c, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]

def stv_ranking(ballots, candidates, num_seats):
    quota = floor(len(ballots) / (num_seats + 1)) + 1
    elected, eliminated = [], []
    active = candidates.copy()
    while len(elected) < num_seats and active:
        firsts = [b[0] for b in ballots if b and b[0] in active]
        counts = Counter(firsts)
        for c in active:
            if counts[c] >= quota and c not in elected:
                elected.append(c)
                active.remove(c)
        if len(elected) >= num_seats: break
        still_active = [c for c in active if c not in elected]
        if not still_active: break
        try:
            min_votes = min(counts[c] for c in still_active)
            to_eliminate = sorted([c for c in still_active if counts.get(c, 0) == min_votes])[0]
        except:
            break
        eliminated.append(to_eliminate)
        active.remove(to_eliminate)
        ballots = [[c for c in b if c != to_eliminate] for b in ballots]
    remaining = [c for c in candidates if c not in elected and c not in eliminated]
    return elected + eliminated + remaining

# -------------------------
# σIIA Metric
# -------------------------
def swap_distance(r1, r2):
    pos = {c: i for i, c in enumerate(r1)}
    perm = [pos[c] for c in r2]
    return sum(1 for i in range(len(perm)) for j in range(i + 1, len(perm)) if perm[i] > perm[j])

def sigma_IIA(rule_fn, ballots, candidates, **kwargs):
    full = rule_fn(ballots, candidates, **kwargs)
    M = len(candidates)
    total = 0
    for cand in candidates:
        reduced_ballots = [[c for c in b if c != cand] for b in ballots]
        reduced_cands = [c for c in candidates if c != cand]
        if not reduced_cands:
            continue
        reduced = rule_fn(reduced_ballots, reduced_cands, **kwargs)
        total += swap_distance([c for c in full if c != cand], reduced)
    max_possible = (M - 1) * (M - 2) / 2
    return 1 - (total / (M * max_possible)) if max_possible > 0 else 1.0

# -------------------------
# Main Loop and Boxplot
# -------------------------
base_dir = "/Users/ss2776/Desktop/fairness_project/scot-elex"
all_results = []

for n in range(3, 15):
    folder = os.path.join(base_dir, f"{n}_cands")
    if not os.path.exists(folder):
        continue

    for file in sorted(os.listdir(folder)):
        if not file.endswith(".csv"):
            continue
        try:
            ballots, candidates, num_seats = parse_election_csv(os.path.join(folder, file))
            if len(candidates) != n:
                continue

            borda = sigma_IIA(borda_ranking, ballots, candidates)
            plurality = sigma_IIA(plurality_ranking, ballots, candidates)
            stv = sigma_IIA(stv_ranking, ballots, candidates, num_seats=num_seats)

            all_results.append({"rule": "Borda", "cand_count": n, "sigma": borda})
            all_results.append({"rule": "Plurality", "cand_count": n, "sigma": plurality})
            all_results.append({"rule": "STV", "cand_count": n, "sigma": stv})

        except Exception as e:
            print(f"❌ Failed on {file} ({n} candidates): {e}")

# -------------------------
# Plotting Boxplot
# -------------------------
df_all = pd.DataFrame(all_results)
plt.figure(figsize=(14, 6))
sns.boxplot(data=df_all, x="cand_count", y="sigma", hue="rule")
plt.title(r"Boxplot of $\sigma_{IIA}$ by Candidate Count and Voting Rule", fontsize=16)
plt.xlabel("Number of Candidates", fontsize=14)
plt.ylabel(r"$\sigma_{IIA}$", fontsize=14)
plt.legend(title="Voting Rule")
plt.tight_layout()
plt.show()