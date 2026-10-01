"""Check CSV loading, all four BT metrics, and JSON output on a tiny unanimous election."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from votekit import RankBallot, RankProfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Verify the primary BT collector on a temporary unanimous-election profile.

    Raises:
        subprocess.CalledProcessError: The collector subprocess fails.
        AssertionError: The collector does not produce four metric outputs with scores of one.
        OSError: Temporary inputs or outputs cannot be written or read.
    """
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
        env = {**os.environ, "PYTHONHASHSEED": "0"}
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipelines/bradley_terry/collect_metrics.py"),
                "--settings-file",
                str(settings),
                "--election-type",
                "borda",
                "--n-seats",
                "2",
                "--output-dir",
                str(work / "results"),
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
