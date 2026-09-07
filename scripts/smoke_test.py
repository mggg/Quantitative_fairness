"""Check CSV loading, all four BT metrics, and JSON output on a tiny unanimous election."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from votekit import RankBallot, RankProfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="qf-smoke-") as temporary:
        work = Path(temporary)
        folder = (
            work / "02_02" / ("b_proportion_0.5__ALPHA_(1.00,1.00,1.00,1.00)__COHESION_(0.70,0.70)")
        )
        folder.mkdir(parents=True)
        profile = RankProfile(
            ballots=(RankBallot(ranking=tuple(frozenset({c}) for c in "ABCD"), weight=10),)
        )
        profile.to_csv(folder / "profile_0.csv")
        settings = work / "settings.txt"
        settings.write_text(str(folder) + "\n")
        env = {**os.environ, "QF_RESULTS_DIR": str(work / "results"), "PYTHONHASHSEED": "0"}
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipelines/bradley-terry/collect_stats_final_set_v2.py"),
                "--settings-file",
                str(settings),
                "--election-type",
                "borda",
                "--n-seats",
                "2",
                "--n-jobs",
                "1",
            ],
            cwd=ROOT,
            env=env,
            check=True,
        )
        outputs = list((work / "results/stats").rglob("*.json"))
        assert len(outputs) == 4, f"Expected four metric outputs, found {len(outputs)}"
        assert all(json.loads(path.read_text()) == [1.0] for path in outputs)
    print("Smoke example passed: four metric outputs equal 1.0.")


if __name__ == "__main__":
    main()
