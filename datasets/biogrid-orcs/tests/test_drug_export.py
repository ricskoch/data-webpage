"""Tests for the drug page score vectors. Run: python3 -m unittest discover -s datasets/biogrid-orcs/tests"""
import pathlib
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import drug_export  # noqa: E402


def screens():
    return pd.DataFrame({
        "screen_id": ["d1", "d2", "d3", "c1", "c2", "c3"],
        "result_scope": ["all_genes", "hits_only", "all_genes", "all_genes", "all_genes", "all_genes"],
        "primary_score_position": [1, 1, None, 2, 1, 1]})


def candidates():
    return pd.DataFrame({"screen_id": ["d1", "d1", "d2", "d3", "d4"],
                         "control_screen_id": ["c1", "c3", "c1", "c1", None],
                         "match": ["same_study", "same_cell_line", "same_study", "same_study", "none"],
                         "rank": [1, 2, 1, 1, None]})


class Plottable(unittest.TestCase):
    def test_needs_full_list_signed_score_and_a_candidate(self):
        # d2 is hits-only, d3 has no signed score, d4 has no control; c2 is not a candidate of anything
        self.assertEqual(drug_export.plottable_ids(screens(), candidates()), ["c1", "c3", "d1"])


class Scores(unittest.TestCase):
    def results(self):
        return pd.DataFrame({
            "screen_id": pd.Categorical(["d1", "d1", "c1", "c1", "x"]),
            "perturbation_id": pd.Categorical(["entrez:1", "entrez:2", "entrez:1", "entrez:2", "entrez:1"]),
            "score_1": [1.0, 2.0, 9.0, 9.0, 7.0], "score_2": [10.0, 20.0, 30.0, 40.0, 50.0]})

    def test_uses_each_screens_primary_column_and_skips_other_screens(self):
        s = drug_export.primary_scores(self.results(), screens(), ["d1", "c1"])
        got = {(r.screen_id, r.perturbation_id): r.score for r in s.itertuples()}
        self.assertEqual(got, {("d1", "entrez:1"): 1.0, ("d1", "entrez:2"): 2.0,
                               ("c1", "entrez:1"): 30.0, ("c1", "entrez:2"): 40.0})

    def test_duplicates_are_folded_by_median_and_counted(self):
        s = pd.DataFrame({"screen_id": ["a"] * 4, "perturbation_id": ["g1", "g1", "g1", "g2"],
                          "score": [1.0, 5.0, 3.0, np.nan]})
        out, folded = drug_export.collapse_duplicates(s)
        self.assertEqual(out["score"].tolist(), [3.0])
        self.assertEqual(folded, 2)  # three g1 rows became one; the missing g2 score is not a fold


class Vector(unittest.TestCase):
    def test_robust_z_in_perturbation_index_order(self):
        # median 3, MAD 1 -> z = (x - 3) / 1.4826
        s = pd.DataFrame({"perturbation_id": ["a", "b", "c", "d", "e"], "score": [1.0, 2.0, 3.0, 4.0, 5.0]})
        v = drug_export.screen_vector(s, {"e": 0, "d": 1, "c": 2, "b": 3, "a": 4})
        self.assertEqual(v["i"], [0, 1, 2, 3, 4])
        self.assertEqual(v["z"], [round(2 / 1.4826, 2), round(1 / 1.4826, 2), 0.0, round(-1 / 1.4826, 2),
                                  round(-2 / 1.4826, 2)])

    def test_flat_screen_has_no_vector(self):
        s = pd.DataFrame({"perturbation_id": ["a", "b", "c"], "score": [1.0, 1.0, 1.0]})
        self.assertIsNone(drug_export.screen_vector(s, {"a": 0, "b": 1, "c": 2}))

    def test_unknown_perturbation_fails_loudly(self):
        s = pd.DataFrame({"perturbation_id": ["a", "zzz", "c"], "score": [1.0, 2.0, 4.0]})
        with self.assertRaises(KeyError):
            drug_export.screen_vector(s, {"a": 0, "c": 2})


if __name__ == "__main__":
    unittest.main()
