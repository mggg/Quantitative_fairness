import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).parents[1].resolve()
sys.path.append(str(ROOT_DIR))

from pipelines.portland.modularity_functions import boost_modularity_matrix  # noqa: E402


def test_modularity_score_4x4():
    test_matrix = np.array(
        [[0, 5, -5, -2], [2, 0, -10, 0], [-10, -1, 0, 12], [-3, 0, 6, 0]]
    )

    test_mod_matrix = boost_modularity_matrix(test_matrix, [0, 0, 1, 1])

    assert test_mod_matrix[0, 1] == 5 - (5 * 5 / 25) + (7 * 1 / 31)
    assert test_mod_matrix[1, 0] == 2 - (2 * 2 / 25) + (10 * 13 / 31)
    assert test_mod_matrix[2, 3] == 12 - (12 * 12 / 25) + (11 * 2 / 31)
    assert test_mod_matrix[3, 2] == 6 - (6 * 6 / 25) + (3 * 15 / 31)
