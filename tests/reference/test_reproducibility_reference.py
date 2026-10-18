"""Independent reference test (spec section 14) for the reproducibility scores: compare
datasets/reproducibility/reproducibility.py with SciPy. Run: python -m unittest discover -s tests/reference
"""
import pathlib
import sys
import unittest

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "datasets" / "reproducibility"))
import reproducibility as rp  # noqa: E402


class ReproducibilityMatchesScipy(unittest.TestCase):
    def test_spearman_matches_scipy_with_and_without_ties(self):
        g = np.random.default_rng(5)
        for n, shift, noise in [(50, 0.0, 1.0), (500, 1.0, 0.5), (3000, 1.0, 2.0), (200, -1.0, 0.1)]:
            x = g.normal(size=n)
            y = np.round(shift * x + g.normal(scale=noise, size=n), 1)  # rounding makes ties
            self.assertAlmostEqual(rp.spearman(x, y), stats.spearmanr(x, y).statistic, places=10)

    def test_overlap_matches_a_plain_set_calculation(self):
        g = np.random.default_rng(8)
        idx = np.arange(1000)
        za = g.normal(size=1000)
        zb = za + g.normal(scale=0.5, size=1000)  # correlated, so the overlap is not zero
        top = lambda z: {int(i) for i in np.argsort(-np.abs(z), kind="stable")[:50]}
        n, _, overlap, expected = rp.compare({"i": idx, "z": za}, {"i": idx, "z": zb}, top=50)
        self.assertEqual((n, overlap, expected), (1000, len(top(za) & top(zb)), 2.5))
