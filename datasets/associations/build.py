"""Precomputed associations: for every gene, does its essential-scale value differ between two groups of cell lines?

Same method as the biological workflow on /gene (src/scripts/workflow.ts), run for all genes at once, plus a
Benjamini-Hochberg false discovery rate (FDR) per question. Questions: each tissue against all other tissues, and each
driver-panel gene mutated against wild-type. Inputs are the published staging site files (URL or local folder).

Usage: python3 -I build.py <work_dir> [screens_base] [context_base]
Writes <work_dir>/site/assoc/index.json and f/NNN.json (what the site loads) and <work_dir>/out/report.md.
Needs numpy (installed with datasets/biogrid-orcs/requirements.txt). Statistics are checked against SciPy in
tests/reference/test_associations_reference.py.
"""
import gzip
import json
import math
import pathlib
import sys
import urllib.request
from collections import defaultdict

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "data-webpage-pipeline (https://github.com/ricskoch/data-webpage)"}
SCREENS = "https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/biogrid-orcs/0.1.0-staging/site"
CONTEXT = "https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/cell-line-context/0.1.0-staging/site/ctx"
MIN_LINES = 5
FDR = 0.05
MIN_EFFECT = 0.2   # the page's default; by_gene.json lists only genes called at q <= FDR with at least this effect
PER_GENE = 6       # strongest calls kept per gene in by_gene.json
# Textbook cases that must come out right on real data: [question, gene, expected sign of the effect, why].
KNOWN = [
    ("mut:KRAS", "KRAS", -1, "KRAS-mutant lines need KRAS"),
    ("mut:BRAF", "BRAF", -1, "BRAF-mutant lines need BRAF"),
    ("mut:PIK3CA", "PIK3CA", -1, "PIK3CA-mutant lines need PIK3CA"),
    ("mut:TP53", "MDM2", 1, "MDM2 matters only while TP53 works"),
]


def read_json(base, path):
    """JSON from a URL or a local folder; the server may or may not have gzip-decoded it."""
    if str(base).startswith("http"):
        req = urllib.request.Request(f"{base}/{path}", headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    else:
        raw = (pathlib.Path(base) / path).read_bytes()
    return json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)


def average_ranks(x):
    """1-based ranks, ties share the mean of the ranks they span."""
    order = np.argsort(x, kind="mergesort")
    s = x[order]
    start = np.concatenate(([0], np.flatnonzero(s[1:] != s[:-1]) + 1))
    end = np.concatenate((start[1:], [len(s)]))
    ranks = np.empty(len(x))
    ranks[order] = np.repeat((start + end + 1) / 2, end - start)
    return ranks, end - start


def mann_whitney(a, b):
    """(U of a, two-sided p): normal approximation with tie and continuity correction. p is NaN if every value is tied."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    n = na + nb
    ranks, ties = average_ranks(np.concatenate((a, b)))
    u = ranks[:na].sum() - na * (na + 1) / 2
    s = math.sqrt(na * nb / 12 * (n + 1 - (ties**3 - ties).sum() / (n * (n - 1))))
    if s <= 0:
        return u, math.nan
    z = (max(u, na * nb - u) - na * nb / 2 - 0.5) / s
    return u, min(1.0, math.erfc(z / math.sqrt(2)))


def benjamini_hochberg(p):
    """FDR-adjusted p-values (q) for the non-NaN entries of p; NaN stays NaN."""
    p = np.asarray(p, float)
    q = np.full(len(p), np.nan)
    ok = np.flatnonzero(~np.isnan(p))
    order = ok[np.argsort(p[ok], kind="mergesort")]
    scaled = p[order] * len(order) / np.arange(1, len(order) + 1)
    q[order] = np.minimum(1.0, np.minimum.accumulate(scaled[::-1])[::-1])
    return q


def line_values(rows, screen_line, n_lines):
    """One value per cell line: the median of that line's screens on the essential scale (NaN where there is none)."""
    by_line = defaultdict(list)
    for r in rows:
        line, value = screen_line.get(r[0]), r[2]
        if line is not None and value is not None:
            by_line[line].append(value)
    out = np.full(n_lines, np.nan)
    for line, vs in by_line.items():
        out[line] = float(np.median(vs))
    return out


def questions(lines, min_lines=MIN_LINES):
    """[(id, label, a name, b name, in group A mask, compared mask)]: tissues vs the rest, driver mutations vs wild-type."""
    fine = np.array([not l.get("problematic") for l in lines])
    out = []
    lineage = [l.get("lineage") for l in lines]
    for t in sorted({t for t in lineage if t}):
        inc = fine & np.array([x is not None for x in lineage])
        a = inc & np.array([x == t for x in lineage])
        if a.sum() >= min_lines and (inc & ~a).sum() >= min_lines:
            out.append((f"tissue:{t}", f"{t} vs all other tissues", t, "all other tissues", a, inc))
    calls = fine & np.array([l.get("mutation_calls") is not False for l in lines])
    mutated = defaultdict(set)
    for i, l in enumerate(lines):
        for d in l.get("drivers") or []:
            mutated[d.split()[0]].add(i)
    for g in sorted(mutated):
        a = calls & np.array([i in mutated[g] for i in range(len(lines))])
        if a.sum() >= min_lines and (calls & ~a).sum() >= min_lines:
            out.append((f"mut:{g}", f"{g}-mutant vs wild-type lines", f"{g}-mutant", "wild-type", a, calls))
    return out


def test_question(matrix, a_mask, inc_mask, min_lines=MIN_LINES):
    """Per gene (row of matrix): effect, p, lines in A, lines in B. Genes with too few lines in a group get NaN."""
    n = matrix.shape[0]
    eff, p = np.full(n, np.nan), np.full(n, np.nan)
    na, nb = np.zeros(n, int), np.zeros(n, int)
    for i in range(n):
        row = matrix[i]
        a, b = row[a_mask & ~np.isnan(row)], row[inc_mask & ~a_mask & ~np.isnan(row)]
        na[i], nb[i] = len(a), len(b)
        if len(a) >= min_lines and len(b) >= min_lines:
            eff[i] = float(np.median(a) - np.median(b))
            p[i] = mann_whitney(a, b)[1]
    return eff, p, na, nb


def sig3(x):
    return None if x is None or math.isnan(x) else float(f"{x:.3g}")


def build(screens_base, context_base, site):
    genes = read_json(screens_base, "genes.json")
    screens = read_json(screens_base, "screens.json")
    ctx = read_json(context_base, "lines.json")
    lines = ctx["lines"]
    screen_line = {i: ctx["screen_line"][str(s["screen_id"])] for i, s in enumerate(screens)
                   if str(s["screen_id"]) in ctx["screen_line"]}
    symbol = {}
    for sym, (pid, shard) in sorted(genes.items()):
        symbol.setdefault((pid, shard), sym)
    by_shard = defaultdict(list)
    for (pid, shard), sym in symbol.items():
        by_shard[shard].append((pid, sym))
    names, rows = [], []
    for shard in sorted(by_shard):
        part = read_json(screens_base, f"g/{int(shard):04d}.json")
        for pid, sym in by_shard[shard]:
            v = line_values(part.get(pid, []), screen_line, len(lines))
            if (~np.isnan(v)).sum() >= 2 * MIN_LINES:
                names.append(sym)
                rows.append(v)
    order = np.argsort(names)
    names = [names[i] for i in order]
    matrix = np.vstack([rows[i] for i in order]) if rows else np.empty((0, len(lines)))
    (site / "f").mkdir(parents=True, exist_ok=True)
    index, checks = [], []
    results = {}
    called = defaultdict(list)  # gene index -> [(q, question number, effect)]
    for n, (qid, label, a_name, b_name, a_mask, inc) in enumerate(questions(lines)):
        eff, p, na, nb = test_question(matrix, a_mask, inc)
        q = benjamini_hochberg(p)
        keep = np.flatnonzero(~np.isnan(p))
        results[qid] = (names, eff, p, q)
        for i in np.flatnonzero(~np.isnan(q) & (q <= FDR) & (np.abs(np.nan_to_num(eff)) >= MIN_EFFECT)):
            called[int(i)].append((float(q[i]), n, float(eff[i])))
        (site / "f" / f"{n:03d}.json").write_text(json.dumps({
            "g": keep.tolist(), "d": [round(float(eff[i]), 4) for i in keep], "p": [sig3(p[i]) for i in keep],
            "q": [sig3(q[i]) for i in keep], "na": na[keep].tolist(), "nb": nb[keep].tolist()}, separators=(",", ":")))
        index.append({"id": qid, "label": label, "a": a_name, "b": b_name, "file": f"f/{n:03d}.json",
                      "lines_a": int((a_mask & inc).sum()), "lines_b": int((inc & ~a_mask).sum()),
                      "tested": int(len(keep)), "significant": int((q[keep] < FDR).sum())})
    for qid, gene, sign, why in KNOWN:
        if qid in results and gene in names:
            i = names.index(gene)
            _, eff, p, q = results[qid]
            ok = bool(not math.isnan(q[i]) and q[i] < FDR and eff[i] * sign > 0)
            checks.append((qid, gene, why, ok, float(eff[i]), float(q[i])))
        else:
            checks.append((qid, gene, why, False, math.nan, math.nan))
    (site / "by_gene.json").write_text(json.dumps({
        "questions": [q["id"] for q in index], "fdr": FDR, "min_effect": MIN_EFFECT,
        "genes": {str(g): [[n, round(d, 3), sig3(qv)] for qv, n, d in sorted(v)[:PER_GENE]] for g, v in sorted(called.items())}},
        separators=(",", ":")))
    (site / "index.json").write_text(json.dumps({
        "release": ctx.get("release"), "min_lines": MIN_LINES, "fdr": FDR, "genes": names, "questions": index},
        separators=(",", ":")))
    return index, checks, len(names), len(lines)


def report(index, checks, n_genes, n_lines):
    out = ["# Associations build report", "", f"{n_genes} genes with values in at least {2 * MIN_LINES} of {n_lines} cell lines; "
           f"{len(index)} questions; false discovery rate {FDR}.", "", "| Question | Lines A | Lines B | Genes tested | q < 0.05 |", "|---|---|---|---|---|"]
    out += [f"| {q['label']} | {q['lines_a']} | {q['lines_b']} | {q['tested']} | {q['significant']} |" for q in index]
    out += ["", "## Known biology (must all pass)", "", "| Question | Gene | Why | Effect | q | Result |", "|---|---|---|---|---|---|"]
    out += [f"| {qid} | {g} | {why} | {e:.3f} | {q:.2g} | {'PASS' if ok else 'FAIL'} |" for qid, g, why, ok, e, q in checks]
    return "\n".join(out) + "\n"


def main(work, screens_base=SCREENS, context_base=CONTEXT):
    work = pathlib.Path(work)
    site, out = work / "site" / "assoc", work / "out"
    site.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    index, checks, n_genes, n_lines = build(screens_base, context_base, site)
    text = report(index, checks, n_genes, n_lines)
    (out / "report.md").write_text(text)
    print(text)
    return 0 if all(c[3] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
