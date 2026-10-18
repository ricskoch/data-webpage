"""Tests for the prototype site bundle."""
import pathlib
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import export_site  # noqa: E402


class ExportSite(unittest.TestCase):
    def test_add_primary_score_joins_object_position_to_integer_position(self):
        # after add_treatment the screens table is object-typed, score_defs.position is int64 (failed on real data)
        screens = pd.DataFrame({"screen_id": ["a", "b"], "primary_score_position": [2.0, np.nan]}).astype(object)
        screens = screens.where(screens.notna(), None)
        defs = pd.DataFrame({"screen_id": ["a", "a", "b"], "position": [1, 2, 1],
                             "native_name": ["x", "DrugZ", "y"]})
        out = export_site.add_primary_score(screens, defs, ["a"])
        self.assertEqual(out["primary_score_name"].tolist(), ["DrugZ", None])
        self.assertEqual(out["has_z"].tolist(), [True, False])
        self.assertEqual(out["primary_score_position"].tolist(), [2.0, None])

    def test_shard_is_stable_and_in_range(self):
        self.assertEqual(export_site.shard_of("entrez:7157"), export_site.shard_of("entrez:7157"))
        self.assertTrue(0 <= export_site.shard_of("orcs:77294U") < export_site.N_SHARDS)

    def test_nan_becomes_null(self):
        self.assertIsNone(export_site.num(float("nan")))
        self.assertEqual(export_site.num(0.123456), 0.1235)

    def test_gene_rows_keep_every_row(self):
        r = pd.DataFrame({"perturbation_id": ["entrez:1", "entrez:1", "entrez:2"], "screen_id": ["a", "b", "a"],
                          "effect_rank": [0.1, np.nan, 0.9], "effect_scaled": [np.nan] * 3,
                          "effect_z": [-1.0, np.nan, 2.0], "hit_source": [True, False, False],
                          "score_1": [-0.5, 3.0, 1.0]})
        shards = export_site.gene_rows(r, {"a": 0, "b": 1})
        g1 = shards[export_site.shard_of("entrez:1")]["entrez:1"]
        self.assertEqual(g1, [[0, 0.1, None, -1.0, 1, -0.5], [1, None, None, None, 0, 3.0]])
        self.assertEqual(sum(len(v) for s in shards.values() for v in s.values()), 3)

    def test_treatment_joined_to_screens(self):
        screens = pd.DataFrame({"screen_id": ["orcs:1", "orcs:2"], "experimental_setup": ["Drug Exposure", "Timecourse"]})
        cond = pd.DataFrame({"screen_id": ["orcs:1"], "agent_label": ["Olaparib"], "dose_raw": ["5.0 \u00b5M"],
                             "duration": [None]})
        out = export_site.add_treatment(screens, cond)
        self.assertEqual(out["treatment"].tolist(), ["Olaparib", None])
        self.assertEqual(out["treatment_dose"].tolist(), ["5.0 \u00b5M", None])
        self.assertEqual(len(out), 2)  # untreated screens are kept, not dropped

    def test_treatment_rejects_two_conditions_per_screen(self):
        screens = pd.DataFrame({"screen_id": ["orcs:1"]})
        cond = pd.DataFrame({"screen_id": ["orcs:1", "orcs:1"], "agent_label": ["A", "B"], "dose_raw": [None, None],
                             "duration": [None, None]})
        with self.assertRaises(ValueError):
            export_site.add_treatment(screens, cond)

    def test_treatment_category(self):
        screens = pd.DataFrame({"screen_id": ["1", "2", "3", "4"],
                                "experimental_setup": ["Drug Exposure", "Drug Exposure", "Timecourse", "Timecourse"],
                                "treatment": ["Olaparib", "3D spheroid growth", "Hypoxia", None]})
        out = export_site.add_treatment_category(screens)
        self.assertEqual(out["treatment_category"].tolist(),
                         ["drug_compound", "culture_format", "condition_change", "untreated"])

    def test_non_drug_screen_with_unknown_name_stays_unclassified(self):
        screens = pd.DataFrame({"screen_id": ["1"], "experimental_setup": ["Timecourse"], "treatment": ["Zorbex"]})
        self.assertEqual(export_site.add_treatment_category(screens)["treatment_category"].tolist(), ["unclassified"])

    def test_drug_pairs_keep_rank_order_and_unmatched_screens(self):
        c = pd.DataFrame({"screen_id": ["d1", "d1", "d2"], "control_screen_id": ["c2", "c1", None],
                          "match": ["same_study_library", "same_cell_line", "none"], "rank": [1, 2, None]})
        self.assertEqual(export_site.drug_pairs(c),
                         {"d1": [["c2", "same_study_library"], ["c1", "same_cell_line"]], "d2": []})


if __name__ == "__main__":
    unittest.main()
