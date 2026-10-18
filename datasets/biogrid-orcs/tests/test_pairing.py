"""Tests for linking drug screens to no-drug screens. Run: python3 -m unittest discover -s datasets/biogrid-orcs/tests"""
import pathlib
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pairing  # noqa: E402


def scr(sid, study, cell, lib="TKOv3", setup="Timecourse", treatment=None, scope="all_genes"):
    return {"screen_id": sid, "study_id": study, "cell_line_label": cell, "library_name": lib,
            "experimental_setup": setup, "treatment": treatment, "result_scope": scope}


class CellKey(unittest.TestCase):
    def test_spelling_variants_match(self):
        self.assertEqual(pairing.cell_key("HAP-1"), pairing.cell_key("HAP1"))
        self.assertEqual(pairing.cell_key("hTERT-RPE1"), pairing.cell_key("hTERT RPE-1"))
        self.assertNotEqual(pairing.cell_key("K-562"), pairing.cell_key("A-549"))

    def test_missing_label_never_matches(self):
        self.assertIsNone(pairing.cell_key(None))
        self.assertIsNone(pairing.cell_key("-"))


class Candidates(unittest.TestCase):
    def setUp(self):
        self.screens = pd.DataFrame([
            scr("d1", "A", "HAP1", setup="Drug Exposure", treatment="Olaparib"),
            scr("c_lib", "A", "HAP-1"),                       # same study, same library
            scr("c_otherlib", "A", "HAP1", lib="Brunello"),   # same study, other library
            scr("c_x1", "B", "HAP1", lib="Brunello"),         # other study, same cell line, other library
            scr("c_x2", "C", "HAP1"),                         # other study, same library: ranked first
            scr("c_hits", "A", "HAP1", scope="hits_only"),    # hits only: useless as a control
            scr("c_virus", "A", "HAP1", setup="Virus Exposure", treatment="Zika"),  # treated: not a control
            scr("c_k562", "A", "K562"),                       # other cell line
            scr("d2", "D", "Jurkat", setup="Drug Exposure", treatment="JQ1"),  # no control anywhere
        ])

    def test_match_levels_and_order(self):
        c = pairing.control_candidates(self.screens, max_other_study=5)
        d1 = c[c["screen_id"] == "d1"]
        self.assertEqual(d1["control_screen_id"].tolist(), ["c_lib", "c_otherlib", "c_x2", "c_x1"])
        self.assertEqual(d1["match"].tolist(), ["same_study_library", "same_study", "same_cell_line",
                                                "same_cell_line"])
        self.assertEqual(d1["rank"].tolist(), [1, 2, 3, 4])

    def test_other_study_candidates_are_capped(self):
        c = pairing.control_candidates(self.screens, max_other_study=1)
        self.assertEqual(c[c["screen_id"] == "d1"]["control_screen_id"].tolist(), ["c_lib", "c_otherlib", "c_x2"])

    def test_unmatched_drug_screen_is_reported_not_dropped(self):
        c = pairing.control_candidates(self.screens)
        d2 = c[c["screen_id"] == "d2"]
        self.assertEqual(len(d2), 1)
        self.assertIsNone(d2["control_screen_id"].iloc[0])
        self.assertEqual(d2["match"].iloc[0], "none")

    def test_only_drug_screens_get_candidates(self):
        c = pairing.control_candidates(self.screens)
        self.assertEqual(sorted(c["screen_id"].unique()), ["d1", "d2"])

    def test_control_without_a_signed_score_is_not_a_candidate_when_the_column_exists(self):
        s = self.screens.assign(primary_score_position=1.0)
        s.loc[s["screen_id"] == "c_lib", "primary_score_position"] = None
        c = pairing.control_candidates(s)
        self.assertNotIn("c_lib", c["control_screen_id"].tolist())
        self.assertEqual(c[c["screen_id"] == "d1"]["match"].iloc[0], "same_study")

    def test_summary_counts_best_match(self):
        s = pairing.summary(pairing.control_candidates(self.screens))
        self.assertEqual(s, {"drug_screens": 2, "best_match": {"same_study_library": 1, "none": 1}})


if __name__ == "__main__":
    unittest.main()
