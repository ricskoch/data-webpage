"""Tests for the cell line context matcher. Run: python3 -m unittest discover -s datasets/cell-line-context/tests"""
import io
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import context  # noqa: E402

CELLOSAURUS = """\
ID   HeLa
AC   CVCL_0030
SY   HELA; Hela; HeLa-CCL2
DR   DepMap; ACH-001086
DR   Cell_Model_Passport; SIDM00136
DI   NCIt; C27677; Human papillomavirus-related endocervical adenocarcinoma
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
SX   Female
CA   Cancer cell line
//
ID   MDA-MB-231
AC   CVCL_0062
SY   MDA-MB231; MDAMB231
DR   DepMap; ACH-000768
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
SX   Female
CA   Cancer cell line
//
ID   A-375
AC   CVCL_0132
SY   A375
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
CA   Cancer cell line
//
ID   SK-N-AS
AC   CVCL_1700
SY   SKNAS
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
CA   Cancer cell line
//
ID   SKNAS-X
AC   CVCL_9999
SY   SKNAS
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
CA   Cancer cell line
//
ID   KB
AC   CVCL_0372
CC   Problematic cell line: Contaminated. Shown to be a HeLa derivative.
OX   NCBI_TaxID=9606; ! Homo sapiens (Human)
CA   Cancer cell line
//
ID   HeLa
AC   CVCL_M000
OX   NCBI_TaxID=10090; ! Mus musculus (Mouse)
CA   Cancer cell line
//
"""


def records():
    return list(context.parse_cellosaurus(io.StringIO(CELLOSAURUS)))


class ParseTests(unittest.TestCase):
    def test_fields(self):
        hela = records()[0]
        self.assertEqual(hela["accession"], "CVCL_0030")
        self.assertEqual(hela["name"], "HeLa")
        self.assertEqual(hela["synonyms"], ["HELA", "Hela", "HeLa-CCL2"])
        self.assertEqual(hela["depmap_id"], "ACH-001086")
        self.assertEqual(hela["sanger_id"], "SIDM00136")
        self.assertEqual(hela["taxon"], "9606")
        self.assertEqual(hela["sex"], "Female")
        self.assertEqual(hela["disease"], "Human papillomavirus-related endocervical adenocarcinoma")
        self.assertFalse(hela["problematic"])

    def test_problematic_flag(self):
        kb = [r for r in records() if r["name"] == "KB"][0]
        self.assertTrue(kb["problematic"])
        self.assertIn("HeLa derivative", kb["problem_note"])


class NormalizeTests(unittest.TestCase):
    def test_case_and_punctuation(self):
        self.assertEqual(context.normalize("MDA-MB-231"), context.normalize("mda mb 231"))
        self.assertEqual(context.normalize("A-375"), "A375")
        self.assertEqual(context.normalize("  HeLa "), "HELA")


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.index = context.build_index(records(), taxon="9606")

    def test_exact_name(self):
        self.assertEqual(context.match("HeLa", self.index)[:2], ("CVCL_0030", "exact_name"))

    def test_human_only(self):
        # The mouse "HeLa" record must not create an ambiguity.
        self.assertEqual(context.match("HeLa", self.index)[0], "CVCL_0030")

    def test_normalized_name(self):
        self.assertEqual(context.match("A375", self.index)[:2], ("CVCL_0132", "synonym"))
        self.assertEqual(context.match("MDA MB 231", self.index)[:2], ("CVCL_0062", "normalized_name"))

    def test_ambiguous_is_not_guessed(self):
        ac, method, note = context.match("SKNAS", self.index)
        self.assertIsNone(ac)
        self.assertEqual(method, "ambiguous")
        self.assertIn("CVCL_1700", note)
        self.assertIn("CVCL_9999", note)

    def test_name_beats_synonym(self):
        # "SK-N-AS" is the primary name of CVCL_1700 even though "SKNAS" is a synonym of two lines.
        self.assertEqual(context.match("SK-N-AS", self.index)[0], "CVCL_1700")

    def test_not_found(self):
        self.assertEqual(context.match("Primary T cells", self.index)[:2], (None, "not_found"))

    def test_override_wins(self):
        ac, method, _ = context.match("SKNAS", self.index, overrides={"SKNAS": "CVCL_1700"})
        self.assertEqual((ac, method), ("CVCL_1700", "manual"))

    def test_override_to_unknown_accession_is_rejected(self):
        with self.assertRaises(ValueError):
            context.match("SKNAS", self.index, overrides={"SKNAS": "CVCL_NOPE"})


class MapScreensTests(unittest.TestCase):
    def test_every_screen_kept_and_summarised(self):
        index = context.build_index(records(), taxon="9606")
        screens = [{"screen_id": "1", "cell_line_label": "HeLa"}, {"screen_id": "2", "cell_line_label": "HeLa"},
                   {"screen_id": "3", "cell_line_label": "SKNAS"}, {"screen_id": "4", "cell_line_label": None}]
        rows, summary = context.map_screens(screens, index)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["cellosaurus_id"] for r in rows], ["CVCL_0030", "CVCL_0030", None, None])
        self.assertEqual(rows[3]["method"], "missing_label")
        self.assertEqual(summary["screens"], 4)
        self.assertEqual(summary["screens_mapped"], 2)
        self.assertEqual(summary["lines"], 2)
        self.assertEqual(summary["lines_mapped"], 1)
        self.assertEqual(summary["screens_with_depmap"], 2)
        self.assertEqual(summary["by_method"], {"exact_name": 2, "ambiguous": 1, "missing_label": 1})


class DepMapListingTests(unittest.TestCase):
    LISTING = [
        {"release": "DepMap Public 24Q2", "release_date": "2024-05-01", "filename": "Model.csv", "url": "u1"},
        {"release": "DepMap Public 25Q2", "release_date": "2025-05-20", "filename": "Model.csv", "url": "u2"},
        {"release": "DepMap Public 25Q2", "release_date": "2025-05-20",
         "filename": "OmicsExpressionProteinCodingGenesTPMLogp1.csv", "url": "u3"},
        {"release": "Sanger CRISPR (Project Score)", "release_date": "2026-01-01", "filename": "Model.csv",
         "url": "u4"},
        {"release": "DepMap Public 25Q2", "release_date": "2025-05-20", "filename": "OmicsSomaticMutations.csv",
         "url": "u5"},
    ]

    def test_latest_public_release_and_patterns(self):
        want = {"models": r"^Model\.csv$", "expression": r"^OmicsExpression.*ProteinCoding.*TPMLogp1.*\.csv$",
                "mutations": r"^OmicsSomaticMutations\.csv$", "copy_number": r"^OmicsCNGene.*\.csv$"}
        release, files, missing = context.pick_depmap_files(self.LISTING, want, release_pattern=r"^DepMap Public")
        self.assertEqual(release, "DepMap Public 25Q2")
        self.assertEqual(files["models"]["url"], "u2")
        self.assertEqual(files["expression"]["url"], "u3")
        self.assertEqual(missing, ["copy_number"])


class FigshareListingTests(unittest.TestCase):
    def test_articles_become_listing_rows(self):
        articles = [{"id": 1, "title": "DepMap 25Q2 Public", "published_date": "2025-05-20T10:00:00Z",
                     "license": {"name": "CC BY 4.0"}},
                    {"id": 2, "title": "Something else", "published_date": "2026-01-01T00:00:00Z"}]
        files = {1: [{"name": "Model.csv", "download_url": "https://ndownloader.figshare.com/files/9", "size": 512,
                      "computed_md5": "abc"}]}
        rows = context.figshare_listing(articles, files, title_pattern=r"^DepMap .*Public")
        self.assertEqual(rows, [{"release": "DepMap 25Q2 Public", "release_date": "2025-05-20", "filename": "Model.csv",
                                 "url": "https://ndownloader.figshare.com/files/9", "size": "512", "md5": "abc",
                                 "licence": "CC BY 4.0"}])


if __name__ == "__main__":
    unittest.main()
