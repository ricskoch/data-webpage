import json
import math
import pathlib
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import reproducibility as rp  # noqa: E402


class Spearman(unittest.TestCase):
    def test_same_order_is_one_and_reverse_is_minus_one(self):
        self.assertAlmostEqual(rp.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(rp.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)

    def test_hand_calculation_with_a_tie(self):  # ranks (1, 2.5, 2.5, 4) and (1, 2, 3, 4): r = 0.9486833
        self.assertAlmostEqual(rp.spearman([1, 2, 2, 5], [1, 2, 3, 4]), 0.9486833, places=6)

    def test_constant_input_gives_nan(self):
        self.assertTrue(math.isnan(rp.spearman([1, 1, 1, 1], [1, 2, 3, 4])))


class Overlap(unittest.TestCase):
    def test_top_genes_use_absolute_z_and_break_ties_by_index(self):
        idx, z = np.array([5, 6, 7, 8]), np.array([-3.0, 3.0, 1.0, -1.0])
        self.assertEqual(rp.top_genes(idx, z, 2), {5, 6})
        self.assertEqual(rp.top_genes(idx, z, 3), {5, 6, 7})  # 7 and 8 tie on |z|: lower index wins

    def test_compare_uses_shared_genes_only(self):
        a = {"i": [0, 1, 2, 3, 4, 5], "z": [5, 4, 0, 0, 0, 9]}  # gene 5 is not in b
        b = {"i": [0, 1, 2, 3, 4, 6], "z": [4, 5, 0, 0, 1, 9]}
        n, rho, overlap, expected = rp.compare(a, b, top=2)
        self.assertEqual(n, 5)
        self.assertEqual(overlap, 2)            # genes 0 and 1 lead in both
        self.assertAlmostEqual(expected, 4 / 5)  # 2 x 2 / 5 shared genes
        self.assertGreater(rho, 0.8)


def vec(genes, z):
    return {"i": list(range(genes)), "z": [float(v) for v in z]}


class Build(unittest.TestCase):
    def setUp(self):
        g = np.random.default_rng(1)
        base = g.normal(size=3000)
        self.dir = pathlib.Path(tempfile.mkdtemp())
        (self.dir / "s").mkdir()
        spec = [  # (treatment, category, line, study, score name, vector)
            ("Olaparib", "drug_compound", "HeLa", "s1", "DrugZ", base),
            ("Olaparib", "drug_compound", "HeLa", "s2", "DrugZ", base + g.normal(scale=0.3, size=3000)),
            ("Olaparib", "drug_compound", "HeLa", "s2", "Log2FC", base),             # other score type: skipped
            ("Olaparib", "drug_compound", "K562", "s1", "DrugZ", base),              # alone in its line: no pair
            ("Hypoxia", "condition_change", "HeLa", "s1", "DrugZ", base),            # not a drug
            ("Cisplatin", "drug_compound", "HeLa", "s1", "DrugZ", base[:100]),
            ("Cisplatin", "drug_compound", "HeLa", "s3", "DrugZ", base[:100]),       # too few shared genes
        ]
        self.screens = []
        for k, (t, c, line, study, score, v) in enumerate(spec):
            self.screens.append({"screen_id": str(k + 1), "study_id": study, "treatment": t, "treatment_category": c,
                                 "cell_line_label": line, "primary_score_name": score, "has_z": True})
            (self.dir / "s" / f"{k:04d}.json").write_text(json.dumps(vec(len(v), v)))
        (self.dir / "screens.json").write_text(json.dumps(self.screens))

    def test_groups_hold_drug_screens_of_one_line_with_two_or_more(self):
        self.assertEqual(rp.eligible(self.screens), {("Cisplatin", "HeLa"): [5, 6], ("Olaparib", "HeLa"): [0, 1, 2]})

    def test_pairs_and_every_skip_with_its_reason(self):
        site = self.dir / "site"
        pairs, skipped, groups = rp.build(self.dir, site)
        self.assertEqual(len(pairs), 1)
        drug, line, a, b, n, rho, overlap, expected, same = pairs[0]
        self.assertEqual((drug, line, a, b, n, same), ("Olaparib", "HeLa", 0, 1, 3000, 0))
        self.assertGreater(rho, 0.9)
        self.assertGreater(overlap, expected * 5)  # far above chance
        self.assertEqual(sorted((s[4]) for s in skipped), ["different score types", "different score types", "too few shared genes"])
        saved = json.loads((site / "repro" / "pairs.json").read_text())
        self.assertEqual(saved["pairs"], json.loads(json.dumps(pairs)))
        self.assertEqual(saved["top"], 200)
        self.assertIn("1 pairs of screens were scored, 3 were skipped", rp.report(pairs, skipped, groups))


if __name__ == "__main__":
    unittest.main()
