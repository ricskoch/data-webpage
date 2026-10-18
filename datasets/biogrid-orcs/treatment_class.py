"""Sort treatment labels into kinds (drug, condition change, culture format...). Rules live in treatment_classes.yaml.

A label can have several parts ("Mutation: BRCA1 | Olaparib"). Each part is sorted by the first matching rule, else
"drug_compound" if the name is a known compound, else "unclassified". The label takes the most specific part:
biological agent > drug > culture format > condition change > unclassified.
"""
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drug_names  # noqa: E402

RULES_PATH = pathlib.Path(__file__).resolve().parent / "treatment_classes.yaml"
PRIORITY = ["biological_agent", "drug_compound", "culture_format", "condition_change", "genetic_background", "unclassified"]


def load_rules(path=RULES_PATH):
    rules = yaml.safe_load(pathlib.Path(path).read_text())
    rules["rules"] = [{**r, "regex": re.compile(r["pattern"], re.I)} for r in rules["rules"]]
    return rules


def classify_part(part, rules, known_compounds):
    for r in rules["rules"]:
        if r["regex"].search(part):
            return r["category"]
    return "drug_compound" if part in known_compounds else "unclassified"


def classify(label, rules, known_compounds=frozenset()):
    if label is None or not str(label).strip():
        return "untreated"
    parts = drug_names.split_label(label)
    if not parts["components"]:
        return "genetic_background" if parts["background"] else "untreated"
    found = {classify_part(p, rules, known_compounds) for p in parts["components"]}
    return next(c for c in PRIORITY if c in found)


def classify_all(labels, rules, known_compounds=frozenset()):
    return {label: classify(label, rules, known_compounds) for label in labels}


def summary(mapping):
    counts = {}
    for c in mapping.values():
        counts[c] = counts.get(c, 0) + 1
    return counts
