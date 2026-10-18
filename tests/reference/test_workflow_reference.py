"""Independent reference test (spec section 14) for biological workflow 2: compare src/scripts/workflow.ts with SciPy.

Runs the TypeScript implementation through node and checks Mann-Whitney U and p against
scipy.stats.mannwhitneyu (asymptotic, continuity-corrected) and the bootstrap interval against
scipy.stats.bootstrap (percentile method). Run: python -m unittest discover -s tests/reference
"""
import json
import pathlib
import subprocess
import unittest

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[2]


def cases():
    g = np.random.default_rng(7)
    out = [
        ([1, 2, 3], [4, 5, 6]),
        ([-1.2, -0.8, -0.8, -0.5, -0.9], [0.1, -0.2, 0.0, 0.0, -0.1, 0.3]),  # ties
    ]
    for na, nb, shift in [(8, 40, -0.6), (25, 120, -0.15), (60, 60, 0.0), (12, 300, 0.4)]:
        a = np.round(g.normal(shift, 0.35, na), 2)  # rounding creates ties, as real scores have
        b = np.round(g.normal(0, 0.35, nb), 2)
        out.append((a.tolist(), b.tolist()))
    return out


class WorkflowMatchesScipy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = cases()
        run = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", "tests/reference/run_workflow.mjs"],
                             input=json.dumps(cls.cases), capture_output=True, text=True, cwd=ROOT, check=True)
        cls.ours = json.loads(run.stdout)

    def test_mann_whitney(self):
        for (a, b), r in zip(self.cases, self.ours):
            ref = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic", use_continuity=True)
            self.assertAlmostEqual(r["u"], ref.statistic, places=9)
            self.assertLess(abs(r["p"] - ref.pvalue), 1e-6 + 1e-5 * ref.pvalue, (a, b))

    def test_difference_and_bootstrap_interval(self):
        for (a, b), r in zip(self.cases, self.ours):
            self.assertAlmostEqual(r["diff"], np.median(a) - np.median(b), places=12)
            ref = stats.bootstrap((np.array(a), np.array(b)),
                                  lambda x, y, axis: np.median(x, axis=axis) - np.median(y, axis=axis),
                                  method="percentile", n_resamples=20000, vectorized=True, random_state=0)
            lo, hi = ref.confidence_interval
            tol = 0.02 + 0.15 * (hi - lo)  # Monte Carlo error of two different random streams
            self.assertLess(abs(r["ci"][0] - lo), tol, (a, b, r["ci"], (lo, hi)))
            self.assertLess(abs(r["ci"][1] - hi), tol, (a, b, r["ci"], (lo, hi)))


if __name__ == "__main__":
    unittest.main()
