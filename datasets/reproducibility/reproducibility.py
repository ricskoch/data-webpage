"""Reproducibility of repeated drug screens: when the same drug was screened in the same cell line more than once, how
well do the screens agree? Two numbers per pair of screens, on the genes both screens report (method chosen by Richard
2026-10-18, "Rho plus hit overlap"):

  rho      Spearman rank correlation of the two screens' scores (1 = same order, 0 = unrelated).
  overlap  how many of each screen's 200 strongest genes (largest absolute robust z) are the same, next to the number
           expected by chance (200 x 200 / shared genes).

Scores are the per-screen robust z of the native primary score, as the /drug page uses them (s/NNNN.json). A rank
correlation depends on the sign of the score, so only screens with the same native score name are paired; every other
pair is written to out/skipped.csv with its reason, never dropped silently.

Usage: python3 -I reproducibility.py <work_dir> [screens_base]
Writes <work_dir>/site/repro/pairs.json (what the site loads), <work_dir>/out/report.md and out/skipped.csv.
Needs numpy. Spearman is checked against SciPy in tests/reference/test_reproducibility_reference.py.
"""
import csv
import itertools
import json
import math
import pathlib
import sys
from collections import defaultdict

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "associations"))
import build as assoc  # noqa: E402  (read_json, average_ranks)

SCREENS = assoc.SCREENS
TOP = 200          # strongest genes compared per screen
MIN_SHARED = 2000  # fewer shared genes than this and the pair is not scored


def spearman(x, y):
    """Spearman rank correlation: Pearson correlation of the average ranks. NaN if either side is constant."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return math.nan
    rx, ry = assoc.average_ranks(x)[0], assoc.average_ranks(y)[0]
    rx, ry = rx - rx.mean(), ry - ry.mean()
    denom = math.sqrt(float((rx**2).sum() * (ry**2).sum()))
    return math.nan if denom == 0 else float((rx * ry).sum() / denom)


def top_genes(index, z, n=TOP):
    """The n genes with the largest absolute z (ties broken by gene index, so the result is repeatable)."""
    order = np.lexsort((index, -np.abs(z)))
    return set(index[order[:n]].tolist())


def compare(a, b, top=TOP):
    """(shared genes, rho, overlap, expected overlap) for two vectors {i, z}; overlap is taken among shared genes."""
    ai, bi = np.asarray(a["i"]), np.asarray(b["i"])
    shared, ia, ib = np.intersect1d(ai, bi, return_indices=True)
    za, zb = np.asarray(a["z"], float)[ia], np.asarray(b["z"], float)[ib]
    n = len(shared)
    k = min(top, n)
    overlap = len(top_genes(shared, za, k) & top_genes(shared, zb, k))
    return n, spearman(za, zb), overlap, (k * k / n if n else math.nan)


def eligible(screens):
    """Groups {(drug, cell line): [screen index]} of drug/compound screens that have a published vector, 2 or more."""
    groups = defaultdict(list)
    for i, s in enumerate(screens):
        if s.get("has_z") and s.get("treatment_category") == "drug_compound" and s.get("treatment") and s.get("cell_line_label"):
            groups[(s["treatment"], s["cell_line_label"])].append(i)
    return {k: v for k, v in sorted(groups.items()) if len(v) > 1}


def r3(x):
    return None if x is None or math.isnan(x) else round(float(x), 3)


def build(screens_base, site):
    screens = assoc.read_json(screens_base, "screens.json")
    cache = {}

    def vector(i):
        if i not in cache:
            try:
                cache[i] = assoc.read_json(screens_base, f"s/{i:04d}.json")
            except Exception:  # a screen whose vector was not published
                cache[i] = None
        return cache[i]

    pairs, skipped = [], []
    groups = eligible(screens)
    for (drug, line), members in groups.items():
        for a, b in itertools.combinations(members, 2):
            sa, sb = screens[a], screens[b]
            why = None
            if sa.get("primary_score_name") != sb.get("primary_score_name"):
                why = ("different score types", f"{sa.get('primary_score_name')} / {sb.get('primary_score_name')}")
            elif vector(a) is None or vector(b) is None:
                why = ("no score vector", "for one of the screens")
            if why is None:
                n, rho, ov, exp = compare(vector(a), vector(b))
                if n < MIN_SHARED:
                    why = ("too few shared genes", f"{n}, minimum {MIN_SHARED}")
                elif math.isnan(rho):
                    why = ("no spread", "scores of one screen are all equal")
            if why:
                skipped.append((drug, line, sa["screen_id"], sb["screen_id"], *why))
                continue
            pairs.append([drug, line, a, b, n, r3(rho), ov, r3(exp), int(sa["study_id"] == sb["study_id"])])
    (site / "repro").mkdir(parents=True, exist_ok=True)
    (site / "repro" / "pairs.json").write_text(json.dumps(
        {"top": TOP, "min_shared": MIN_SHARED, "columns": ["drug", "cell_line", "screen_a", "screen_b", "shared_genes", "rho", "overlap", "expected_overlap", "same_study"],
         "pairs": pairs}, separators=(",", ":")))
    return pairs, skipped, groups


def report(pairs, skipped, groups):
    rho = np.array([p[5] for p in pairs], float)
    out = ["# Reproducibility build report", "",
           f"{len(groups)} drug and cell line combinations have two or more screens with a score vector. "
           f"{len(pairs)} pairs of screens were scored, {len(skipped)} were skipped (reasons in skipped.csv).", ""]
    if len(rho):
        out += ["| | pairs |", "|---|---|", f"| rho 0.5 or higher | {int((rho >= 0.5).sum())} |",
                f"| rho between 0.2 and 0.5 | {int(((rho >= 0.2) & (rho < 0.5)).sum())} |", f"| rho below 0.2 | {int((rho < 0.2).sum())} |",
                f"| median rho | {np.median(rho):.2f} |", ""]
    reasons = defaultdict(int)
    for s in skipped:
        reasons[s[4]] += 1
    out += [f"- skipped, {r}: {n}" for r, n in sorted(reasons.items())]
    return "\n".join(out) + "\n"


def main(work, screens_base=SCREENS):
    work = pathlib.Path(work)
    site, out = work / "site", work / "out"
    out.mkdir(parents=True, exist_ok=True)
    pairs, skipped, groups = build(screens_base, site)
    (out / "report.md").write_text(report(pairs, skipped, groups))
    with open(out / "skipped.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["drug", "cell_line", "screen_a", "screen_b", "reason", "detail"])
        w.writerows(skipped)
    print((out / "report.md").read_text())


if __name__ == "__main__":
    main(*sys.argv[1:3])
