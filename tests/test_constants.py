"""Check that the shared BT grid covers the preserved replication inputs."""

from itertools import product
from pathlib import Path

from voting_metrics_main_code.constants import (
    BT_ALPHA_COMBINATIONS,
    BT_BLOC_PROPORTIONS,
    BT_CANDIDATE_COMBINATIONS,
    BT_COHESION_COMBINATIONS,
)


def test_bt_grid_matches_preserved_profile_manifest():
    settings = {
        f"data/preference_profiles/{n_a:02d}_{n_b:02d}/b_proportion_{b_prop}"
        f"__ALPHA_({aa:.2f},{ab:.2f},{ba:.2f},{bb:.2f})"
        f"__COHESION_({a_coh:.2f},{b_coh:.2f})"
        for (n_a, n_b), b_prop, (a_coh, b_coh), (aa, ab, ba, bb) in product(
            BT_CANDIDATE_COMBINATIONS,
            BT_BLOC_PROPORTIONS,
            BT_COHESION_COMBINATIONS,
            BT_ALPHA_COMBINATIONS,
        )
    }
    manifest = Path(__file__).resolve().parents[1] / "config/bt_profiles.txt"
    assert settings == set(manifest.read_text().splitlines())
