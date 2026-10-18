import json
import math
import pathlib
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build  # noqa: E402


class Ranks(unittest.TestCase):
    def test_ties_share_the_mean_rank(self):
        ranks, ties = build.average_ranks(np.array([3.0, 1.0, 3.0, 2.0]))
        self.assertEqual(ranks.tolist(), [3.5, 1.0, 3.5, 2.0])
        self.assertEqual(sorted(ties.tolist()), [1, 1, 2])


class MannWhitney(unittest.TestCase):
    def test_separated_samples(self):  # hand calculation: U = 0, z = 1.7457, p = 0.0809
        u, p = build.mann_whitney([1, 2, 3], [4, 5, 6])
        self.assertEqual(u, 0)
        self.assertAlmostEqual(p, 0.0809, places=3)

    def test_all_values_tied_gives_no_p(self):
        self.assertTrue(math.isnan(build.mann_whitney([1, 1], [1, 1, 1])[1]))

    def test_p_does_not_depend_on_which_sample_is_first(self):
        a, b = [1.0, 2.0, 2.0, 9.0], [3.0, 4.0, 5.0, 2.0, 8.0]
        self.assertAlmostEqual(build.mann_whitney(a, b)[1], build.mann_whitney(b, a)[1])


class BenjaminiHochberg(unittest.TestCase):
    def test_hand_example(self):
        q = build.benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
        np.testing.assert_allclose(q, [0.02, 0.04, 0.04, 0.02])

    def test_nan_is_left_out_of_the_count_and_stays_nan(self):
        q = build.benjamini_hochberg([0.01, math.nan, 0.04])
        self.assertTrue(math.isnan(q[1]))
        np.testing.assert_allclose([q[0], q[2]], [0.02, 0.04])

    def test_never_above_one(self):
        self.assertEqual(build.benjamini_hochberg([0.9, 0.95]).max(), 0.95)


class LineValues(unittest.TestCase):
    def test_median_per_line_skips_missing_scores_and_unmapped_screens(self):
        rows = [[0, 0.1, -1.0], [1, 0.2, -0.5], [2, 0.3, -0.2], [3, 0.4, None], [9, 0.5, -3.0]]
        v = build.line_values(rows, {0: 0, 1: 0, 2: 1, 3: 2}, 3)
        self.assertEqual(v[0], -0.75)
        self.assertEqual(v[1], -0.2)
        self.assertTrue(math.isnan(v[2]))


def lines(n, lineage, drivers=(), problematic=(), no_calls=(), lof=(), gof=()):
    """lof/gof: genes carried as loss-of-function / hotspot mutation by the first 8 lines (also listed in drivers)."""
    return [{"lineage": lineage, "problematic": i in problematic, "drivers": [f"{d} p.X1Y" for d in (*drivers, *lof, *gof) if i < 8],
             "drivers_lof": [d for d in lof if i < 8], "drivers_gof": [d for d in gof if i < 8],
             **({"mutation_calls": False} if i in no_calls else {})} for i in range(n)]


class Questions(unittest.TestCase):
    def test_tissues_and_driver_mutations_need_enough_lines_in_both_groups(self):
        ls = lines(8, "Lung", drivers=["KRAS"]) + lines(8, "Skin") + lines(3, "Rare")
        ids = [q[0] for q in build.questions(ls)]
        self.assertEqual(ids, ["tissue:Lung", "tissue:Skin", "mut:KRAS"])  # "Rare" has 3 lines

    def test_flagged_lines_and_lines_without_mutation_calls_are_left_out(self):
        ls = lines(14, "Lung", drivers=["KRAS"], problematic={0}, no_calls={1})
        (_, _, _, _, a, inc), = [q for q in build.questions(ls) if q[0] == "mut:KRAS"]
        self.assertFalse(inc[0] or inc[1])
        self.assertEqual(int(a.sum()), 6)  # lines 2 to 7; the mutated lines 0 and 1 are excluded

    def test_loss_and_gain_of_function_are_compared_with_wild_type_lines_only(self):
        # lines 0-7 carry TP53 loss of function, lines 8-15 a TP53 hotspot, 16-19 a passenger missense, 20-39 are wild-type
        ls = lines(40, "Lung")
        for i in range(8):
            ls[i].update(drivers=["TP53 p.R1*"], drivers_lof=["TP53"])
        for i in range(8, 16):
            ls[i].update(drivers=["TP53 p.R175H"], drivers_gof=["TP53"])
        for i in range(16, 20):
            ls[i].update(drivers=["TP53 p.A1B"])
        qs = {q[0]: q for q in build.questions(ls)}
        self.assertEqual(sorted(k for k in qs if k.startswith("mut")), ["mut:TP53", "mutgof:TP53", "mutlof:TP53"])
        _, label, a_name, b_name, a, inc = qs["mutlof:TP53"]
        self.assertEqual((int(a.sum()), int(inc.sum())), (8, 28))  # 8 loss of function + 20 wild-type
        self.assertEqual(np.flatnonzero(a).tolist(), list(range(8)))
        self.assertFalse(inc[8:20].any())  # hotspot and passenger lines are neither group
        self.assertEqual((a_name, b_name), ("TP53 loss-of-function", "wild-type"))
        self.assertIn("loss-of-function", label)
        self.assertEqual(np.flatnonzero(qs["mutgof:TP53"][4]).tolist(), list(range(8, 16)))

    def test_a_line_with_both_classes_in_one_gene_is_in_neither_class_nor_wild_type(self):
        ls = lines(30, "Lung")
        for i in range(8):
            ls[i].update(drivers=["KRAS p.G12D", "KRAS p.R1*"], drivers_lof=["KRAS"], drivers_gof=["KRAS"])
        ids = [q[0] for q in build.questions(ls)]
        self.assertNotIn("mutlof:KRAS", ids)
        self.assertNotIn("mutgof:KRAS", ids)

    def test_files_without_class_lists_give_no_class_questions(self):
        ls = [{k: v for k, v in l.items() if k not in ("drivers_lof", "drivers_gof")} for l in lines(20, "Lung", drivers=["KRAS"])]
        self.assertEqual([q[0] for q in build.questions(ls)], ["mut:KRAS"])


class TestQuestion(unittest.TestCase):
    def test_planted_effect_and_too_few_lines(self):
        g = np.random.default_rng(1)
        m = g.normal(0, 0.1, (3, 30))
        m[0, :10] -= 1.0  # gene 0 depends on group A (the first ten lines)
        m[2, 5:] = np.nan  # gene 2 has only five lines in A and none in B
        a = np.arange(30) < 10
        eff, p, na, nb = build.test_question(m, a, np.ones(30, bool))
        self.assertLess(eff[0], -0.8)
        self.assertLess(p[0], 1e-4)
        self.assertGreater(p[1], 0.01)
        self.assertTrue(math.isnan(eff[2]) and math.isnan(p[2]))
        self.assertEqual((na[2], nb[2]), (5, 0))


class EndToEnd(unittest.TestCase):
    def test_build_writes_index_and_per_question_files(self):
        n = 24
        ls = lines(12, "Lung", drivers=["KRAS"]) + lines(12, "Skin")
        ctx = {"release": "test", "lines": ls, "screen_line": {f"s{i}": i for i in range(n)}}
        genes = {"KRAS": ["p1", 0], "NEUTRAL": ["p2", 0], "TOOFEW": ["p3", 0]}
        g = np.random.default_rng(2)
        shard = {"p1": [[i, 0.5, -1.0 + 0.05 * g.random() if i < 6 else 0.05 * g.random(), 0, 0, 0] for i in range(n)],
                 "p2": [[i, 0.5, 0.1 * g.random(), 0, 0, 0] for i in range(n)],
                 "p3": [[0, 0.5, -1.0, 0, 0, 0]]}
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "g").mkdir()
            (d / "genes.json").write_text(json.dumps(genes))
            (d / "screens.json").write_text(json.dumps([{"screen_id": f"s{i}"} for i in range(n)]))
            (d / "g" / "0000.json").write_text(json.dumps(shard))
            (d / "lines.json").write_text(json.dumps(ctx))
            site = d / "site"
            index, checks, n_genes, n_lines = build.build(d, d, site)
            self.assertEqual((n_genes, n_lines), (2, 24))  # TOOFEW has one line only
            top = json.loads((site / "index.json").read_text())
            self.assertEqual(top["genes"], ["KRAS", "NEUTRAL"])
            kras = next(q for q in top["questions"] if q["id"] == "mut:KRAS")
            f = json.loads((site / kras["file"]).read_text())
            i = f["g"].index(0)  # KRAS is gene 0
            self.assertLess(f["d"][i], -0.8)
            self.assertLess(f["q"][i], 0.05)
            self.assertTrue(any(c[0] == "mut:KRAS" and c[3] for c in checks))
            by_gene = json.loads((site / "by_gene.json").read_text())
            self.assertIn("mut:KRAS", by_gene["questions"])
            n, d, q = by_gene["genes"]["0"][0]  # KRAS is gene 0: its strongest call is the KRAS-mutant question
            self.assertEqual(by_gene["questions"][n], "mut:KRAS")
            self.assertLess(d, -0.8)
            self.assertLess(q, 0.05)
            self.assertNotIn("1", by_gene["genes"])  # NEUTRAL is never called


if __name__ == "__main__":
    unittest.main()
