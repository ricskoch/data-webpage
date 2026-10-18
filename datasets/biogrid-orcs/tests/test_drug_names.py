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
        self.assertEqual(drug_names.summary(m), {"mapped": 2, "review": 1, "unmapped": 0, "background_only": 1})

    def test_parallel_lookup_gives_the_same_mapping_and_reports_progress(self):
        labels = ["Olaparib", "Mutation: BRCA2 KO | Olaparib", "Olaparib + A159"]
        seen = []
        serial = drug_names.build_mapping(labels, fake(OLAPARIB))
        par = drug_names.build_mapping(labels, fake(OLAPARIB), workers=4, progress=lambda d, n, name: seen.append((d, n)))
        self.assertEqual(par, serial)
        self.assertEqual(seen, [(1, 2), (2, 2)])


if __name__ == "__main__":
    unittest.main()
