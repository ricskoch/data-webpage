import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import display_names  # noqa: E402
import treatment_class  # noqa: E402

RULES = treatment_class.load_rules()


class CellLine(unittest.TestCase):
    def test_hyphens_and_whitespace_removed_and_upper_case(self):
        for raw, want in (("HCT 116", "HCT116"), ("MDA-MB-231", "MDAMB231"), ("hela", "HELA"),
                          ("  K 562 ", "K562"), ("A549", "A549"), ("NCI-H1299", "NCIH1299")):
            self.assertEqual(display_names.cell_line(raw), want, raw)

    def test_other_characters_are_kept(self):
        self.assertEqual(display_names.cell_line("HAP1 (KO)"), "HAP1(KO)")

    def test_missing_stays_missing(self):
        self.assertIsNone(display_names.cell_line(None))
        self.assertIsNone(display_names.cell_line("  "))


class Drug(unittest.TestCase):
    def test_first_letter_capital(self):
        for raw, want in (("olaparib", "Olaparib"), ("Olaparib", "Olaparib"), ("mitomycin C", "Mitomycin C"),
                          ("5-fluorouracil", "5-Fluorouracil"), ("cisplatin", "Cisplatin")):
            self.assertEqual(display_names.drug(raw), want, raw)

    def test_code_like_names_with_many_digits_are_all_caps(self):
        for raw, want in (("AZD5576", "AZD5576"), ("gsk461364", "GSK461364"), ("Cpd-391", "CPD-391"),
                          ("bi-2536", "BI-2536"), ("OTA-3998", "OTA-3998")):
            self.assertEqual(display_names.drug(raw), want, raw)

    def test_few_digits_do_not_make_a_code(self):
        self.assertEqual(display_names.drug("Interleukin-2"), "Interleukin-2")

    def test_shouting_plain_words_are_softened_but_short_acronyms_stay(self):
        self.assertEqual(display_names.drug("OLAPARIB"), "Olaparib")
        self.assertEqual(display_names.drug("DMSO"), "DMSO")
        self.assertEqual(display_names.drug("BPDE"), "BPDE")

    def test_inner_capitals_are_kept(self):
        self.assertEqual(display_names.drug("nutlin-3a"), "Nutlin-3a")
        self.assertEqual(display_names.drug("ATRi"), "ATRi")


class Treatment(unittest.TestCase):
    def show(self, label):
        return display_names.treatment(label, RULES, frozenset(), None)

    def test_drug_components_are_formatted_and_joined_as_before(self):
        known = frozenset({"olaparib", "azd5576"})
        self.assertEqual(display_names.treatment("olaparib + azd5576", RULES, known, None), "Olaparib + AZD5576")

    def test_other_kinds_and_background_are_left_as_written(self):
        self.assertEqual(self.show("3D spheroid growth"), "3D spheroid growth")
        self.assertEqual(self.show("hypoxia"), "hypoxia")
        self.assertEqual(self.show("Mutation: tp53"), "Mutation: tp53")

    def test_drug_with_background_part(self):
        known = frozenset({"olaparib"})
        self.assertEqual(display_names.treatment("olaparib | Mutation: BRCA1", RULES, known, None),
                         "Olaparib | Mutation: BRCA1")

    def test_no_label(self):
        self.assertIsNone(self.show(None))


class Collisions(unittest.TestCase):
    def test_reports_raw_labels_that_share_a_display_name(self):
        out = display_names.collisions(["HCT 116", "HCT116", "HeLa", "K-562"])
        self.assertEqual(out, {"HCT116": ["HCT 116", "HCT116"]})


if __name__ == "__main__":
    unittest.main()
