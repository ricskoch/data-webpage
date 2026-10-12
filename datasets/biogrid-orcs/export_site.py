"""Prototype site bundle: small JSON files the website reads directly (spec 6.4, hot lookup tables as JSON).

Usage: python3 -I export_site.py <work_dir>   (reads <work_dir>/out/*.parquet, writes <work_dir>/site/)

screens.json   one row per screen: label, context, treatment, normalization status (the data overview)
summary.json   counts for the overview page
drug_pairs.json  drug screen -> ranked "no drug" screens [[control screen_id, match level], ...] (pairing.py)
genes.json     symbol -> [perturbation_id, shard] for the lookup box
g/<NN>.json    per-perturbation rows: [screen index, effect_rank, effect_scaled, effect_z, hit, native score]
"""
import hashlib
import json
import math
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pairing  # noqa: E402

N_SHARDS = 1024
SCREEN_FIELDS = ["screen_id", "study_id", "cell_line_label", "library_name", "perturbation_type", "selection_type",
                 "phenotype", "experimental_setup", "scoring_method", "result_scope", "normalization_status",
                 "direction", "direction_evidence", "known_biology_pass"]


def shard_of(perturbation_id):
    """Stable shard number from the ID (not Python's hash, which changes between runs)."""
    return int(hashlib.sha1(perturbation_id.encode()).hexdigest(), 16) % N_SHARDS


def num(x, digits=4):
    """JSON-safe rounded float; NaN becomes null."""
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), digits)


def screen_table(screens, studies, results):
    counts = results.groupby("screen_id", observed=True).agg(rows=("source_row", "size"), hits=("hit_source", "sum"))
    s = screens.merge(studies[["study_id", "author_label", "year"]], on="study_id", how="left")
    s = s.merge(counts, left_on="screen_id", right_index=True, how="left")
    out = s[SCREEN_FIELDS + ["author_label", "year", "rows", "hits"]].astype(object)
    return out.where(out.notna(), None)


def add_treatment(screens, conditions):
    """Attach the named condition (drug, virus, toxin...) and its dose to each screen, as the source wrote them.

    Untreated screens keep None. ORCS has at most one condition per screen; more would need a new layout, so fail.
    """
    if conditions["screen_id"].duplicated().any():
        raise ValueError("more than one condition for a screen; the site bundle expects at most one")
    c = conditions[["screen_id", "agent_label", "dose_raw", "duration"]].rename(
        columns={"agent_label": "treatment", "dose_raw": "treatment_dose", "duration": "treatment_duration"})
    out = screens.merge(c, on="screen_id", how="left").astype(object)
    return out.where(out.notna(), None)


def drug_pairs(candidates):
    """{drug screen_id: [[control screen_id, match], ...]} in rank order; [] when no candidate exists."""
    out = {}
    for sid, g in candidates.groupby("screen_id", sort=True):
        out[str(sid)] = [[c, m] for c, m in zip(g["control_screen_id"], g["match"]) if pd.notna(c)]
    return out


def summary(screens):
    top = lambda c, n=12: screens[c].value_counts().head(n).to_dict()
    return {"screens": int(len(screens)), "studies": int(screens["study_id"].nunique()),
            "rows": int(screens["rows"].sum()), "by_status": top("normalization_status"),
            "by_perturbation": top("perturbation_type"), "by_selection": top("selection_type"),
            "top_cell_lines": top("cell_line_label"), "top_phenotypes": top("phenotype"),
            "top_treatments": top("treatment"),
            "by_year": {int(k): int(v) for k, v in screens["year"].dropna().value_counts().sort_index().items()}}


def gene_rows(results, screen_index):
    """Group result rows by perturbation into compact arrays, keyed by shard."""
    r = results[["perturbation_id", "screen_id", "effect_rank", "effect_scaled", "effect_z", "hit_source",
                 "score_1"]].copy()
    r["s"] = r["screen_id"].astype(str).map(screen_index)
    shards = {}
    for pid, g in r.groupby("perturbation_id", observed=True):
        rows = [[int(s), num(a, 3), num(b, 3), num(c, 3), int(h), num(n)] for s, a, b, c, h, n in
                zip(g["s"], g["effect_rank"], g["effect_scaled"], g["effect_z"], g["hit_source"], g["score_1"])]
        shards.setdefault(shard_of(str(pid)), {})[str(pid)] = rows
    return shards


def main(work):
    out, site = work / "out", work / "site"
    (site / "g").mkdir(parents=True, exist_ok=True)
    cols = ["perturbation_id", "screen_id", "effect_rank", "effect_scaled", "effect_z", "hit_source", "score_1",
            "source_row"]
    results = pd.read_parquet(out / "results.parquet", columns=cols)
    screens = screen_table(pd.read_parquet(out / "screens.parquet"), pd.read_parquet(out / "studies.parquet"), results)
    screens = add_treatment(screens, pd.read_parquet(out / "conditions.parquet"))
    index = {sid: i for i, sid in enumerate(screens["screen_id"])}
    (site / "screens.json").write_text(json.dumps(screens.to_dict("records"), separators=(",", ":")))
    candidates = pairing.control_candidates(screens)
    (site / "drug_pairs.json").write_text(json.dumps(drug_pairs(candidates), separators=(",", ":")))
    (site / "summary.json").write_text(json.dumps({**summary(screens), "drug_pairs": pairing.summary(candidates)},
                                                  indent=1))
    pert = pd.read_parquet(out / "perturbations.parquet")
    genes = {str(sym): [str(pid), shard_of(str(pid))] for pid, sym in zip(pert["perturbation_id"], pert["symbol"])}
    (site / "genes.json").write_text(json.dumps(genes, separators=(",", ":")))
    # One shard at a time keeps memory to a few MB of Python objects instead of all 26 M rows.
    pids = results["perturbation_id"].astype("category")
    shard = pids.cat.codes.map(dict(enumerate(shard_of(str(c)) for c in pids.cat.categories)))
    for n, part in results.groupby(shard.to_numpy()):
        rows = gene_rows(part, index).get(int(n), {})
        (site / "g" / f"{int(n):04d}.json").write_text(json.dumps(rows, separators=(",", ":")))
    print(f"wrote {len(index)} screens, {len(genes)} symbols into {site}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(pathlib.Path(sys.argv[1]))
