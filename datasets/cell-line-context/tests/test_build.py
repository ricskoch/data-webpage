"""Tests for the cell line context tables. Run: python3 -m unittest discover -s datasets/cell-line-context/tests"""
import io
import math
import pathlib
import sys
import unittest

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build  # noqa: E402


class GeneColumnTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(build.parse_gene_column("TP53 (7157)"), ("TP53", 7157))
        self.assertEqual(build.parse_gene_column("HLA-A (3105)"), ("HLA-A", 3105))
        self.assertIsNone(build.parse_gene_column("ModelID"))


class MatrixTests(unittest.TestCase):
    CSV = ",TP53 (7157),KRAS (3845),odd column\nACH-1,1.5,0.2,x\nACH-2,0.0,,y\nACH-9,3.0,3.0,z\n"

    def test_keeps_only_wanted_models_and_gene_columns(self):
        long, info = build.read_matrix(io.StringIO(self.CSV), wanted={"ACH-1", "ACH-2"}, chunksize=1)
        self.assertEqual(sorted(long["depmap_id"].unique()), ["ACH-1", "ACH-2"])
        self.assertEqual(set(long["entrez"]), {7157, 3845})
        # missing values are kept as missing, not dropped or set to 0
        self.assertEqual(len(long), 4)
        self.assertTrue(math.isnan(long[(long.depmap_id == "ACH-2") & (long.entrez == 3845)]["value"].iloc[0]))
        self.assertEqual(info["models_read"], 3)
        self.assertEqual(info["models_kept"], 2)
        self.assertEqual(info["ignored_columns"], ["odd column"])

    def test_default_entry_column(self):
        csv = ("SequencingID,ModelID,IsDefaultEntryForModel,TP53 (7157)\n"
               "CDS-1,ACH-1,Yes,1.0\nCDS-2,ACH-1,No,9.0\n")
        long, _ = build.read_matrix(io.StringIO(csv), wanted={"ACH-1"})
        self.assertEqual(long["value"].tolist(), [1.0])


class MutationTests(unittest.TestCase):
    def test_protein_altering_kept_with_flags(self):
        df = pd.DataFrame({
            "ModelID": ["ACH-1", "ACH-1", "ACH-2", "ACH-9"],
            "HugoSymbol": ["TP53", "TTN", "KRAS", "TP53"],
            "EntrezGeneID": [7157, 7273, 3845, 7157],
            "ProteinChange": ["p.R175H", "", "p.G12D", "p.R273H"],
            "VepImpact": ["MODERATE", "LOW", "MODERATE", "MODERATE"],
            "LikelyLoF": [False, False, False, False],
            "Hotspot": [True, False, True, True],
        })
        out, info = build.select_mutations(df, wanted={"ACH-1", "ACH-2"})
        self.assertEqual(out["symbol"].tolist(), ["TP53", "KRAS"])
        self.assertEqual(out["hotspot"].tolist(), [True, True])
        self.assertEqual(info["rows_read"], 4)
        self.assertEqual(info["other_models"], 1)
        self.assertEqual(info["not_protein_altering"], 1)

    def test_missing_required_column_fails_loudly(self):
        with self.assertRaises(KeyError):
            build.select_mutations(pd.DataFrame({"HugoSymbol": ["TP53"]}), wanted={"ACH-1"})


    def test_models_with_calls(self):
        # ACH-3 has only a synonymous call: it still has mutation data (wild-type for TP53, not unknown)
        df = pd.DataFrame({"ModelID": ["ACH-1", "ACH-3", "ACH-9"], "HugoSymbol": ["TP53", "TTN", "TP53"]})
        self.assertEqual(build.models_with_calls(df, {"ACH-1", "ACH-2", "ACH-3"}), {"ACH-1", "ACH-3"})


class LineTableTests(unittest.TestCase):
    def test_join_by_rrid_and_signatures(self):
        mapping = pd.DataFrame({"screen_id": ["1", "2", "3"], "cellosaurus_id": ["CVCL_0030", "CVCL_0030", None],
                                "cellosaurus_name": ["HeLa", "HeLa", None], "problematic": [False, False, None]})
        models = pd.DataFrame({"ModelID": ["ACH-001086"], "RRID": ["CVCL_0030"], "OncotreeLineage": ["Cervix"],
                               "OncotreePrimaryDisease": ["Cervical Adenocarcinoma"], "Sex": ["Female"]})
        sigs = pd.DataFrame({"ModelID": ["ACH-001086"], "Ploidy": [3.1], "WGD": [1], "MSIScore": [0.4]})
        lines = build.line_table(mapping, models, sigs)
        self.assertEqual(len(lines), 1)
        row = lines.iloc[0]
        self.assertEqual(row["depmap_id"], "ACH-001086")
        self.assertEqual(row["lineage"], "Cervix")
        self.assertAlmostEqual(row["ploidy"], 3.1)
        self.assertEqual(row["screens"], 2)


class ShardTests(unittest.TestCase):
    def test_values_aligned_to_line_order(self):
        expr = pd.DataFrame({"depmap_id": ["B", "A"], "entrez": [7157, 7157], "value": [2.0, float("nan")]})
        muts = pd.DataFrame({"depmap_id": ["B"], "entrez": [7157], "protein_change": ["p.R175H"],
                             "likely_lof": [False], "hotspot": [True]})
        packed = build.pack_gene(7157, order=["A", "B", "C"], expr=expr, cn=expr.iloc[0:0], muts=muts)
        self.assertEqual(packed["e"], [None, 2.0, None])
        self.assertEqual(packed["c"], [None, None, None])
        self.assertEqual(packed["m"], [[1, "p.R175H", 0, 1]])


if __name__ == "__main__":
    unittest.main()
