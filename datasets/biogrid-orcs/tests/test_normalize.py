"""Tests for score normalization (spec 12.8). Reference values are computed independently with plain Python."""
import pathlib
import statistics
import sys
import unittest

import numpy as np
import pandas as pd
import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import normalize  # noqa: E402

CONFIG = yaml.safe_load((HERE.parent / "dataset.yaml").read_text())


def ref_rank(values):
    """Independent rank percentile: average rank of ties, (r - 1) / (n - 1)."""
    n = len(values)
    out = []
    for v in values:
        below = sum(1 for w in values if w < v)
        equal = sum(1 for w in values if w == v)
        out.append((below + (equal + 1) / 2 - 1) / (n - 1))
    return out


def ref_robust_z(values):
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    return [(v - med) / (1.4826 * mad) for v in values]


class ScoreDefs(unittest.TestCase):
    def defs(self, *names):
        d = pd.DataFrame({"screen_id": "s", "position": range(1, len(names) + 1), "native_name": names})
        return normalize.classify_scores(d, CONFIG)

    def test_documented_direction(self):
        d = self.defs("CERES score", "FDR").set_index("position")
        self.assertEqual((d.loc[1, "direction"], d.loc[1, "direction_evidence"]), ("lower_is_depleted", "documented"))
        self.assertEqual((d.loc[2, "signed"], d.loc[2, "direction"]), (False, "unsigned"))

    def test_unknown_name_is_signed_with_unknown_direction(self):
        d = self.defs("Brand New Score").iloc[0]
        self.assertEqual((d["method_family"], d["signed"], d["direction"]), ("other", True, "unknown"))

    def test_primary_is_first_signed_score(self):
        d = self.defs("FDR", "Log2FC", "Z-score")
        self.assertEqual(normalize.primary_positions(d)["s"], 2)

    def test_no_signed_score_means_no_primary(self):
        self.assertNotIn("s", normalize.primary_positions(self.defs("FDR", "p-Value")))


class ReferenceSplit(unittest.TestCase):
    def test_halves_are_disjoint_and_deterministic(self):
        a, b = normalize.split_reference({5, 1, 4, 2, 3})
        self.assertEqual((a, b), ({1, 3, 5}, {2, 4}))


class Effects(unittest.TestCase):
    def test_rank_matches_reference_with_ties(self):
        v = [3.0, -1.0, 2.0, 2.0, 0.5]
        np.testing.assert_allclose(normalize.effect_rank(pd.Series(v)), ref_rank(v), atol=1e-12)

    def test_rank_zero_is_most_depleted(self):
        r = normalize.effect_rank(pd.Series([-5.0, 0.0, 5.0]))
        self.assertEqual(list(r), [0.0, 0.5, 1.0])

    def test_robust_z_matches_reference(self):
        v = [1.0, 2.0, 2.5, 4.0, 10.0, -3.0]
        np.testing.assert_allclose(normalize.effect_z(pd.Series(v)), ref_robust_z(v), atol=1e-12)

    def test_robust_z_null_when_mad_is_zero(self):
        self.assertTrue(normalize.effect_z(pd.Series([1.0, 1.0, 1.0, 2.0])).isna().all())

    def test_scaled_puts_neg_at_0_and_ceg_at_minus_1(self):
        s = pd.Series([-2.0, -2.0, 0.0, 0.0, -1.0])
        ceg = pd.Series([True, True, False, False, False])
        neg = pd.Series([False, False, True, True, False])
        self.assertEqual(list(normalize.effect_scaled(s, ceg, neg)), [-1.0, -1.0, 0.0, 0.0, -0.5])


def screen(n_ceg=60, n_neg=60, ceg_value=-2.0, noise=1):
    """Synthetic screen: CEG genes 1..n, NEG genes 1001.., 200 other genes around 0."""
    rng = np.random.default_rng(noise)
    genes = list(range(1, n_ceg + 1)) + list(range(1001, 1001 + n_neg)) + list(range(5001, 5201))
    score = np.r_[ceg_value + rng.normal(0, .2, n_ceg), rng.normal(0, .2, n_neg), rng.normal(0, 1, 200)]
    return pd.DataFrame({"gene_id": pd.array(genes, dtype="Int64"), "score": score}), \
        set(range(1, n_ceg + 1)), set(range(1001, 1001 + n_neg))


META = {"selection_type": "negative", "result_scope": "all_genes", "study_id": "pubmed:1"}


class NormalizeScreen(unittest.TestCase):
    def run_screen(self, df, ceg, neg, direction="unknown", evidence="unresolved", meta=META, nonlinear=False):
        return normalize.normalize_screen(df["score"], df["gene_id"], meta, direction, evidence, nonlinear,
                                          normalize.split_reference(ceg), normalize.split_reference(neg), CONFIG)

    def test_direction_inferred_from_known_biology(self):
        df, ceg, neg = screen(ceg_value=-2.0)
        cols, info = self.run_screen(df, ceg, neg)
        self.assertEqual((info["direction"], info["direction_evidence"]), ("lower_is_depleted", "known_biology_test"))
        self.assertEqual(info["normalization_status"], "anchored")
        self.assertAlmostEqual(float(cols["effect_scaled"][df["gene_id"].isin(neg)].median()), 0.0, delta=0.15)

    def test_reversed_score_is_aligned(self):
        df, ceg, neg = screen(ceg_value=+2.0)
        cols, info = self.run_screen(df, ceg, neg)
        self.assertEqual(info["direction"], "higher_is_depleted")
        self.assertLess(float(cols["effect_rank"][df["gene_id"].isin(ceg)].median()), 0.3)

    def test_no_separation_stays_unknown_and_effects_null(self):
        df, ceg, neg = screen(ceg_value=0.0)
        cols, info = self.run_screen(df, ceg, neg)
        self.assertEqual(info["direction"], "unknown")
        self.assertEqual(info["normalization_status"], "not_comparable")
        self.assertTrue(all(cols[c].isna().all() for c in cols))

    def test_positive_selection_gets_rank_and_z_but_no_scale(self):
        df, ceg, neg = screen()
        cols, info = self.run_screen(df, ceg, neg, "lower_is_depleted", "documented",
                                     meta={**META, "selection_type": "positive"})
        self.assertEqual(info["normalization_status"], "robust_z")
        self.assertTrue(cols["effect_scaled"].isna().all())
        self.assertFalse(cols["effect_rank"].isna().any())

    def test_too_few_reference_genes_not_anchored(self):
        df, ceg, neg = screen(n_ceg=30)
        _, info = self.run_screen(df, ceg, neg, "lower_is_depleted", "documented")
        self.assertEqual((info["normalization_status"], info["n_ceg_present"]), ("robust_z", 30))

    def test_hits_only_screen_not_comparable(self):
        df, ceg, neg = screen()
        cols, info = self.run_screen(df, ceg, neg, "lower_is_depleted", "documented",
                                     meta={**META, "result_scope": "hits_only"})
        self.assertEqual(info["normalization_status"], "not_comparable")
        self.assertTrue(cols["effect_rank"].isna().all())

    def test_known_biology_check_uses_half_b(self):
        df, ceg, neg = screen(ceg_value=-2.0)
        _, info = self.run_screen(df, ceg, neg, "lower_is_depleted", "documented")
        self.assertTrue(info["known_biology_pass"])

    def test_documented_direction_contradicted_is_flagged(self):
        df, ceg, neg = screen(ceg_value=+2.0)
        _, info = self.run_screen(df, ceg, neg, "lower_is_depleted", "documented")
        self.assertFalse(info["known_biology_pass"])

    def test_human_override_wins(self):
        df, ceg, neg = screen(ceg_value=0.0)
        cfg = {**CONFIG, "normalization": {**CONFIG["normalization"],
                                           "direction_overrides": {"pubmed:1": "higher_is_depleted"}}}
        _, info = normalize.normalize_screen(df["score"], df["gene_id"], META, "unknown", "unresolved", False,
                                             normalize.split_reference(ceg), normalize.split_reference(neg), cfg)
        self.assertEqual((info["direction"], info["direction_evidence"]), ("higher_is_depleted", "human_confirmed"))


class ApplyNormalization(unittest.TestCase):
    def test_end_to_end_two_screens(self):
        df, ceg, neg = screen(ceg_value=-2.0)
        a = df.assign(screen_id="s1", score_1=np.nan, score_2=df["score"], gene_id_status="entrez")
        b = df.assign(screen_id="s2", score_1=1.0, score_2=np.nan, gene_id_status="entrez")
        results = pd.concat([a, b], ignore_index=True)
        screens = pd.DataFrame({"screen_id": ["s1", "s2"], "selection_type": "negative",
                                "result_scope": "all_genes", "study_id": "pubmed:1"})
        defs = pd.DataFrame({"screen_id": ["s1", "s1", "s2"], "position": [1, 2, 1],
                             "native_name": ["FDR", "Log2FC", "p-Value"]})
        res, scr, d = normalize.apply_normalization(results, screens, defs, ceg, neg, CONFIG)
        s = scr.set_index("screen_id")
        self.assertEqual((s.loc["s1", "normalization_status"], s.loc["s1", "primary_score_position"]), ("anchored", 2))
        self.assertEqual(s.loc["s2", "normalization_status"], "not_comparable")
        self.assertTrue(res.loc[res.screen_id == "s2", "effect_rank"].isna().all())
        self.assertEqual(d.set_index(["screen_id", "position"]).loc[("s1", 2), "direction_evidence"],
                         "known_biology_test")
        self.assertTrue(normalize.known_biology_summary(res, scr, CONFIG)["passed"])


if __name__ == "__main__":
    unittest.main()
