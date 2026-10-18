import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import treatment_class  # noqa: E402

RULES = treatment_class.load_rules()


def cat(label):
    return treatment_class.classify(label, RULES)


class TreatmentClass(unittest.TestCase):
    def test_no_label_is_untreated(self):
        self.assertEqual(cat(None), "untreated")
        self.assertEqual(cat("  "), "untreated")

    def test_background_only(self):
        self.assertEqual(cat("Mutation: TP53"), "genetic_background")
        self.assertEqual(cat("Mutation: KRAS | Knockout: PTEN"), "genetic_background")

    def test_culture_format(self):
        for label in ("3D spheroid growth", "Organoid culture", "Ultra-low attachment"):
            self.assertEqual(cat(label), "culture_format", label)

    def test_condition_change(self):
        for label in ("Hypoxia", "Glucose starvation", "Serum withdrawal", "Heat shock 42C"):
            self.assertEqual(cat(label), "condition_change", label)

    def test_biological_agent(self):
        for label in ("Influenza A virus", "Salmonella bacteria", "NK cells", "Virus: SARS-CoV-2"):
            self.assertEqual(cat(label), "biological_agent", label)

    def test_unknown_stays_unclassified_not_guessed(self):
        self.assertEqual(cat("Olaparib"), "unclassified")

    def test_drug_when_id_known(self):
        self.assertEqual(treatment_class.classify("Olaparib", RULES, known_compounds={"Olaparib"}), "drug_compound")

    def test_background_plus_compound_is_compound(self):
        self.assertEqual(treatment_class.classify("Mutation: BRCA1 | Olaparib", RULES, known_compounds={"Olaparib"}),
                         "drug_compound")

    def test_rule_beats_known_compound(self):
        # "Hypoxia" must not become a drug because someone listed it
        self.assertEqual(treatment_class.classify("Hypoxia", RULES, known_compounds={"Hypoxia"}), "condition_change")

    def test_every_category_declared(self):
        for r in RULES["rules"]:
            self.assertIn(r["category"], RULES["categories"])

    def test_summary_counts(self):
        s = treatment_class.summary({"A": "unclassified", "B": "condition_change", "C": "unclassified"})
        self.assertEqual(s, {"unclassified": 2, "condition_change": 1})


if __name__ == "__main__":
    unittest.main()
