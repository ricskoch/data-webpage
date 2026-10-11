"""Tests for the BioGRID ORCS adapter. Run: python3 -m unittest discover -s datasets/biogrid-orcs/tests"""
import io
import math
import pathlib
import sys
import unittest

import pandas as pd
import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import adapter  # noqa: E402

CONFIG = yaml.safe_load((HERE.parent / "dataset.yaml").read_text())
HEADER = "#SCREEN_ID\tIDENTIFIER_ID\tIDENTIFIER_TYPE\tOFFICIAL_SYMBOL\tALIASES\tORGANISM_ID\tORGANISM_OFFICIAL\t" \
         "SCORE.1\tSCORE.2\tSCORE.3\tSCORE.4\tSCORE.5\tHIT\tSOURCE\n"


def screen_file(*rows):
    return io.StringIO(HEADER + "".join("\t".join(r) + "\n" for r in rows))


def row(screen="7", ident="533", itype="ENTREZ_GENE", sym="ATP6V0B", s1="-1.5", s2="-", hit="NO", org="9606"):
    return (screen, ident, itype, sym, "-", org, "Homo sapiens", s1, s2, "-", "-", "-", hit, "BioGRID ORCS")


def index_row(**over):
    base = {"SCREEN_ID": "7", "SOURCE_ID": "29083409", "SOURCE_TYPE": "pubmed", "AUTHOR": "Meyers RM (2017)",
            "SCORES_SIZE": "3", "FULL_SIZE_AVAILABLE": "Yes", "NUMBER_OF_HITS": "1", "ANALYSIS": "CERES",
            "SIGNIFICANCE_CRITERIA": "Score.2 (FDR) < 0.05", "SCREEN_TYPE": "Negative Selection",
            "SCREEN_FORMAT": "Pool", "EXPERIMENTAL_SETUP": "Timecourse", "DURATION": "21 Days",
            "CONDITION_NAME": "-", "CONDITION_DOSAGE": "-", "LIBRARY": "Avana", "LIBRARY_TYPE": "CRISPRn",
            "ENZYME": "Cas9", "CELL_LINE": "CAMA-1", "CELL_TYPE": "Breast Adenocarcinoma Cell Line",
            "PHENOTYPE": "cell proliferation", "SCORE_COL_COUNT": "2", "SCORE.1_TYPE": "CERES score",
            "SCORE.2_TYPE": "FDR", "SCORE.3_TYPE": "-", "SCORE.4_TYPE": "-", "SCORE.5_TYPE": "-",
            "ORGANISM_ID": "9606"}
    base.update(over)
    return base


class ReadResults(unittest.TestCase):
    def parse(self, *rows):
        return adapter.parse_screen_file(screen_file(*rows), "7", CONFIG)

    def test_native_scores_kept_and_missing_is_null(self):
        res, rej = self.parse(row(s1="-1.5", s2="0.01"), row(ident="527", s1="2e-3", s2="-"))
        self.assertEqual(list(res["score_1"]), [-1.5, 0.002])
        self.assertEqual(res["score_2"].iloc[0], 0.01)
        self.assertTrue(math.isnan(res["score_2"].iloc[1]))
        self.assertEqual(len(rej), 0)

    def test_source_row_is_line_number_in_file(self):
        res, _ = self.parse(row(), row(ident="527"), row(ident="526"))
        self.assertEqual(list(res["source_row"]), [2, 3, 4])

    def test_duplicate_genes_are_kept_not_collapsed(self):
        res, _ = self.parse(row(s1="-1"), row(s1="-2"))
        self.assertEqual(len(res), 2)
        self.assertEqual(res["perturbation_id"].nunique(), 1)

    def test_entrez_rows_get_gene_id(self):
        res, _ = self.parse(row(ident="533"))
        self.assertEqual(res["gene_id"].iloc[0], 533)
        self.assertEqual(res["perturbation_id"].iloc[0], "entrez:533")
        self.assertEqual(res["gene_id_status"].iloc[0], "entrez")

    def test_controls_and_unknown_ids_kept_with_null_gene_and_reason(self):
        res, rej = self.parse(row(ident="6U", itype="UNKNOWN", sym="NTC"),
                              row(ident="16A", itype="AMBIGUOUS", sym="1-Sep"),
                              row(ident="1U", itype="UNKNOWN", sym="ERCC6-PGBD3"))
        self.assertEqual(len(res), 3)
        self.assertTrue(res["gene_id"].isna().all())
        self.assertEqual(list(res["gene_id_status"]), ["control", "ambiguous_identifier", "unknown_identifier"])
        self.assertEqual(res["perturbation_id"].iloc[0], "orcs:6U")
        self.assertEqual(len(rej), 0)

    def test_hit_parsed_to_boolean(self):
        res, _ = self.parse(row(hit="YES"), row(ident="527", hit="NO"))
        self.assertEqual(list(res["hit_source"]), [True, False])

    def test_bad_rows_rejected_with_reason_not_coerced(self):
        res, rej = self.parse(row(), row(ident="2", s1="abc"), row(ident="3", hit="MAYBE"),
                              row(ident="4", org="10090"), row(screen="8", ident="5"))
        self.assertEqual(len(res), 1)
        self.assertEqual(list(rej["reason"]),
                         ["score_1_not_numeric", "hit_not_yes_no", "organism_not_9606", "screen_id_mismatch"])
        self.assertEqual(list(rej["source_row"]), [3, 4, 5, 6])

    def test_unexpected_columns_raise(self):
        bad = io.StringIO("#SCREEN_ID\tGENE\n7\t1\n")
        with self.assertRaises(adapter.SchemaError):
            adapter.parse_screen_file(bad, "7", CONFIG)


class Screens(unittest.TestCase):
    def test_maps_index_fields(self):
        s = adapter.to_screens(pd.DataFrame([index_row()]), CONFIG).iloc[0]
        self.assertEqual(s["screen_id"], "biogrid-orcs:7")
        self.assertEqual(s["source_screen_id"], "7")
        self.assertEqual(s["study_id"], "pubmed:29083409")
        self.assertEqual(s["perturbation_type"], "knockout")
        self.assertEqual(s["selection_type"], "negative")
        self.assertEqual(s["screen_format"], "monogenic")
        self.assertEqual(s["result_scope"], "all_genes")
        self.assertEqual(s["cell_line_label"], "CAMA-1")

    def test_hits_only_scope(self):
        s = adapter.to_screens(pd.DataFrame([index_row(FULL_SIZE_AVAILABLE="No")]), CONFIG).iloc[0]
        self.assertEqual(s["result_scope"], "hits_only")

    def test_unmapped_value_is_flagged_not_guessed(self):
        s = adapter.to_screens(pd.DataFrame([index_row(LIBRARY_TYPE="CRISPRx")]), CONFIG).iloc[0]
        self.assertEqual(s["perturbation_type"], "unmapped")

    def test_score_defs_one_row_per_native_score(self):
        d = adapter.to_score_defs(pd.DataFrame([index_row()]))
        self.assertEqual(list(d["position"]), [1, 2])
        self.assertEqual(list(d["native_name"]), ["CERES score", "FDR"])


class Conditions(unittest.TestCase):
    def test_dose_split_into_value_and_unit(self):
        c = adapter.to_conditions(pd.DataFrame([index_row(CONDITION_NAME="Etoposide", CONDITION_DOSAGE="130.0 nM",
                                                          EXPERIMENTAL_SETUP="Drug Exposure")])).iloc[0]
        self.assertEqual((c["agent_label"], c["dose"], c["dose_unit"], c["role"]), ("Etoposide", 130.0, "nM", "treatment"))

    def test_unparseable_dose_kept_as_text(self):
        c = adapter.to_conditions(pd.DataFrame([index_row(CONDITION_NAME="IFNG", CONDITION_DOSAGE="IC50")])).iloc[0]
        self.assertTrue(pd.isna(c["dose"]))
        self.assertEqual(c["dose_raw"], "IC50")

    def test_untreated_screen_has_no_condition(self):
        self.assertEqual(len(adapter.to_conditions(pd.DataFrame([index_row()]))), 0)


class CountChecks(unittest.TestCase):
    def test_counts_match(self):
        screens = adapter.to_screens(pd.DataFrame([index_row(SCORES_SIZE="2", NUMBER_OF_HITS="1")]), CONFIG)
        res, rej = adapter.parse_screen_file(screen_file(row(hit="YES"), row(ident="2", s1="x")), "7", CONFIG)
        self.assertEqual(adapter.check_screen_counts(screens, res, rej), [])

    def test_count_mismatch_reported(self):
        screens = adapter.to_screens(pd.DataFrame([index_row(SCORES_SIZE="5", NUMBER_OF_HITS="0")]), CONFIG)
        res, rej = adapter.parse_screen_file(screen_file(row(hit="YES")), "7", CONFIG)
        problems = adapter.check_screen_counts(screens, res, rej)
        self.assertEqual({p["check"] for p in problems}, {"row_count", "hit_count"})


if __name__ == "__main__":
    unittest.main()
