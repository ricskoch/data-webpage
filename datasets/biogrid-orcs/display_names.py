"""Display names for the site: cell lines and drugs written one way, so lists line up.

Display only. The raw labels stay in the export for joins and traceability; these functions never change them.
"""
import re

import drug_names
import treatment_class

CODE_MIN_DIGITS = 3        # a single word with this many digits, and enough of them, is a compound code
CODE_MIN_DIGIT_SHARE = 0.3
SHOUT_MIN_LETTERS = 6      # all-capital plain words this long are softened; short acronyms (DMSO) stay


def cell_line(label):
    """'MDA-MB-231' -> 'MDAMB231': hyphens and whitespace out, upper case. None for no label."""
    if label is None:
        return None
    out = re.sub(r"[-\s]+", "", str(label)).upper()
    return out or None


def _is_code(name):
    if re.search(r"\s", name):
        return False
    digits = sum(c.isdigit() for c in name)
    alnum = sum(c.isalnum() for c in name)
    return digits >= CODE_MIN_DIGITS and digits / alnum >= CODE_MIN_DIGIT_SHARE


def drug(name):
    """'olaparib' -> 'Olaparib'; code-like names with many digits are all caps ('gsk461364' -> 'GSK461364').

    Capitals inside a name are kept ('ATRi', 'Mitomycin C'); only an all-capital plain word of six letters or more
    is lowered to a leading capital ('OLAPARIB' -> 'Olaparib'), so short acronyms such as DMSO stay as they are.
    """
    name = drug_names.norm(str(name))
    if _is_code(name):
        return name.upper()
    letters = [c for c in name if c.isalpha()]
    if (len(letters) >= SHOUT_MIN_LETTERS and all(c.isupper() for c in letters) and not re.search(r"\d", name)
            and not re.search(r"\s", name)):
        name = name.lower()
    for i, c in enumerate(name):
        if c.isalpha():
            return name[:i] + c.upper() + name[i + 1:]
    return name


def treatment(label, rules, known_compounds, curated=None):
    """The treatment label with its drug components formatted by drug(); other kinds and backgrounds are untouched."""
    if label is None or not str(label).strip():
        return None
    out = []
    for part in str(label).split("|"):
        part = drug_names.norm(part)
        if not part:
            continue
        if drug_names.BACKGROUND.match(part):
            out.append(part)
            continue
        comps = [c for c in (drug_names.norm(c) for c in drug_names.split_outside_brackets(part)) if c]
        out.append(" + ".join(drug(c) if treatment_class.classify_part(c, rules, known_compounds, curated)
                              == "drug_compound" else c for c in comps))
    return " | ".join(out)


def collisions(labels):
    """{display name: [raw labels]} where different raw labels share one display name (merge only with a Cellosaurus ID)."""
    by = {}
    for raw in sorted(set(labels)):
        d = cell_line(raw)
        if d:
            by.setdefault(d, []).append(raw)
    return {d: raws for d, raws in by.items() if len(raws) > 1}
