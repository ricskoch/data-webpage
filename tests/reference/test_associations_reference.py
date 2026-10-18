"""Independent reference test (spec section 14) for the precomputed associations: compare
datasets/associations/build.py with SciPy. Run: python -m unittest discover -s tests/reference
"""
import pathlib
import sys
import unittest

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "datasets" / "associations"))
import build  # noqa: E402


class AssociationsMatchScipy(unittest.TestCase):
    def test_mann_whitney_matches_scipy_asymptotic_with_continuity_correction(self):
        g = np.random.default_rng(11)
        cases = [([1, 2, 3], [4, 5, 6]), ([-1.2, -0.8, -0.8, -0.5, -0.9], [0.1, -0.2, 0.0, 0.0, -0.1, 0.3])]
        for na, nb, shift in [(8, 40, -0.6), (25, 120, -0.15), (60, 60, 0.0), (12, 300, 0.4), (5, 5, 0.2)]:
            cases.append((np.round(g.normal(shift, 0.35, na), 2), np.round(g.normal(0, 0.35, nb), 2)))  # rounding makes ties
        for a, b in cases:
            ref = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic", use_continuity=True)
            u, p = build.mann_whitney(a, b)
            self.assertAlmostEqual(u, ref.statistic, places=9)
            self.assertAlmostEqual(p, ref.pvalue, places=9)

    def test_average_ranks_match_scipy(self):
        x = np.round(np.random.default_rng(3).normal(0, 1, 200), 1)
        np.testing.assert_allclose(build.average_ranks(x)[0], stats.rankdata(x))

    def test_benjamini_hochberg_matches_scipy(self):
        g = np.random.default_rng(5)
        p = np.concatenate((g.uniform(0, 1, 500), g.uniform(0, 1e-3, 40)))
        np.testing.assert_allclose(build.benjamini_hochberg(p), stats.false_discovery_control(p, method="bh"))


if __name__ == "__main__":
    unittest.main()
