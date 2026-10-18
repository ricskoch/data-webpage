import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import drug_names  # noqa: E402


def fake(responses):
    """fetch_json stand-in: a dict of url fragment -> payload; anything else is 'not found' (None)."""
    def fetch(url):
        for key, payload in responses.items():
            if key in url:
                return payload
        return None
    return fetch


OLAPARIB = {
    "name/Olaparib/cids": {"IdentifierList": {"CID": [23725625]}},
    "cid/23725625/property": {"PropertyTable": {"Properties": [{"CID": 23725625, "Title": "Olaparib"}]}},
    "q=Olaparib": {"molecules": [{"molecule_chembl_id": "CHEMBL521686", "pref_name": "OLAPARIB"}]},
}


class DrugNames(unittest.TestCase):
    def test_split_plain_label(self):
        self.assertEqual(drug_names.split_label("Olaparib"), {"background": [], "components": ["Olaparib"]})

    def test_split_background_and_drug(self):
        s = drug_names.split_label("Mutation: BRCA2 KO | Olaparib")
        self.assertEqual(s, {"background": ["Mutation: BRCA2 KO"], "components": ["Olaparib"]})

    def test_split_combination(self):
        self.assertEqual(drug_names.split_label("Olaparib  + Cisplatin")["components"], ["Olaparib", "Cisplatin"])

    def test_plus_inside_brackets_does_not_split(self):
        s = drug_names.split_label("Immunotherapy (GVAX + PD-1 blockade)")
        self.assertEqual(s["components"], ["Immunotherapy (GVAX + PD-1 blockade)"])
        self.assertEqual(drug_names.split_label("Olaparib (5 uM) + Cisplatin")["components"],
                         ["Olaparib (5 uM)", "Cisplatin"])

    def test_curated_name_is_looked_up_under_the_reviewed_spelling(self):
        curated = {"Aspariginase": {"canonical": "Olaparib", "kind": "drug_compound", "confidence": "high"}}
        r = drug_names.resolve("Aspariginase", fake(OLAPARIB), curated)
        self.assertEqual((r["status"], r["pubchem_cid"], r["looked_up_as"], r["curated"]), ("mapped", 23725625, "Olaparib", True))
        self.assertEqual(r["name"], "Aspariginase")  # the label as written stays the key

    def test_curated_name_without_canonical_is_not_looked_up(self):
        calls = []
        r = drug_names.resolve("Radiation", lambda u: calls.append(u),
                               {"Radiation": {"canonical": None, "kind": "condition_change", "confidence": "high"}})
        self.assertEqual((r["status"], r["pubchem_cid"], calls), ("no_id", None, []))

    def test_curated_pair_looks_up_both_and_reports_the_worse_status(self):
        base = fake({**OLAPARIB, "name/Weird/cids": {"IdentifierList": {"CID": [1, 2]}}})
        curated = {"A and B": {"canonical": ["Olaparib", "Weird"], "kind": "drug_compound", "confidence": "high"}}
        r = drug_names.resolve("A and B", base, curated)
        self.assertEqual(r["status"], "review")
        self.assertEqual([c["pubchem_cid"] for c in r["compounds"]], [23725625, 1])

    def test_curated_unknown_spelling_stays_unmapped(self):
        curated = {"X": {"canonical": "Nothing", "kind": "drug_compound", "confidence": "low"}}
        self.assertEqual(drug_names.resolve("X", fake({}), curated)["status"], "unmapped")

    def test_resolved_name_gets_both_ids(self):
        r = drug_names.resolve("Olaparib", fake(OLAPARIB))
        self.assertEqual((r["status"], r["pubchem_cid"], r["pubchem_title"], r["chembl_id"]),
                         ("mapped", 23725625, "Olaparib", "CHEMBL521686"))

    def test_several_pubchem_matches_need_review_and_keep_first(self):
        r = drug_names.resolve("X", fake({"name/X/cids": {"IdentifierList": {"CID": [5, 6]}}}))
        self.assertEqual((r["status"], r["pubchem_cid"]), ("review", 5))

    def test_unknown_name_is_unmapped_not_guessed(self):
        r = drug_names.resolve("A159", fake({}))
        self.assertEqual((r["status"], r["pubchem_cid"], r["chembl_id"]), ("unmapped", None, None))

    def test_chembl_needs_an_exact_preferred_name(self):
        f = fake({"q=Olap": {"molecules": [{"molecule_chembl_id": "CHEMBL1", "pref_name": "OLAPARIB"}]}})
        self.assertIsNone(drug_names.chembl_exact("Olap", f))

    def test_each_drug_is_looked_up_once_and_summary_counts_worst_status(self):
        calls = []
        base = fake({**OLAPARIB, "name/Weird/cids": {"IdentifierList": {"CID": [1, 2]}}})

        def counting(url):
            calls.append(url)
            return base(url)
        m = drug_names.build_mapping(["Olaparib", "Mutation: BRCA2 KO | Olaparib", "Olaparib + Weird", "Mutation: TP53 KO"],
                                     counting)
        self.assertEqual(len([u for u in calls if "name/Olaparib/cids" in u]), 1)
        self.assertEqual(drug_names.summary(m), {"mapped": 2, "review": 1, "unmapped": 0, "not_a_compound": 0, "no_id": 0, "background_only": 1})

    def test_parallel_lookup_gives_the_same_mapping_and_reports_progress(self):
        labels = ["Olaparib", "Mutation: BRCA2 KO | Olaparib", "Olaparib + A159"]
        seen = []
        serial = drug_names.build_mapping(labels, fake(OLAPARIB))
        par = drug_names.build_mapping(labels, fake(OLAPARIB), workers=4, progress=lambda d, n, name: seen.append((d, n)))
        self.assertEqual(par, serial)
        self.assertEqual(seen, [(1, 2), (2, 2)])

    def test_bracketed_alias_and_dose_are_handled(self):
        self.assertEqual(drug_names.candidates("GSK461364 (GSK461364A)"), ["GSK461364", "GSK461364A", "GSK461364 (GSK461364A)"])
        self.assertEqual(drug_names.candidates("THZ-1(50nmol/L)")[0], "THZ-1")
        self.assertNotIn("50nmol/L", drug_names.candidates("THZ-1(50nmol/L)"))

    def test_alias_is_used_when_the_main_name_has_no_match(self):
        f = fake({"name/KU-57788/cids": {"IdentifierList": {"CID": [9]}}})
        r = drug_names.resolve("NU 7441 (KU-57788)", f)
        self.assertEqual((r["status"], r["pubchem_cid"], r["looked_up_as"]), ("mapped", 9, "KU-57788"))

    def test_organisms_and_cells_are_not_looked_up(self):
        calls = []
        r = drug_names.resolve("Virus: Human hepatitis A virus HM175", lambda url: calls.append(url))
        self.assertEqual((r["status"], calls), ("not_a_compound", []))
        self.assertEqual(drug_names.resolve("V. parahaemolyticus with active T3SS1", lambda u: None)["status"], "not_a_compound")
        m = {"Virus: X": {"background": [], "components": [{"status": "not_a_compound"}]}}
        self.assertEqual(drug_names.summary(m)["not_a_compound"], 1)


class ReviewedFile(unittest.TestCase):
    """drugs.yaml is hand-reviewed; keep it well-formed."""

    def setUp(self):
        import treatment_class
        self.curated = drug_names.load_curated(pathlib.Path(__file__).resolve().parent.parent / "drugs.yaml")
        self.kinds = set(treatment_class.load_rules()["categories"]) - {"untreated"}

    def test_every_entry_is_complete(self):
        for name, e in self.curated.items():
            self.assertIn(e["kind"], self.kinds, name)
            self.assertIn(e["confidence"], ("high", "medium", "low"), name)
            self.assertTrue(e["canonical"] is None or isinstance(e["canonical"], (str, list)), name)

    def test_names_are_already_split_the_way_the_pipeline_splits(self):
        for name in self.curated:
            self.assertEqual(drug_names.split_label(name)["components"], [name], name)

    def test_only_drugs_get_a_lookup_name(self):
        for name, e in self.curated.items():
            if e["canonical"] is not None:
                self.assertEqual(e["kind"], "drug_compound", name)


if __name__ == "__main__":
    unittest.main()
