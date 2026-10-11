"""Profile an extracted BioGRID ORCS release (M2a). Exploratory: reads files, writes numbers, changes nothing.

Usage: python3 -I profile.py <extracted_dir> <hgnc_complete_set.txt> <CEGv2.txt> <NEGv1.txt> <out.json> [<out.parquet>]

Missing values in ORCS are written as "-". They are counted as null here; nothing is coerced or dropped.
"""
import collections
import glob
import json
import os
import re
import sys

import pandas as pd

NA = {"-", ""}


def read_tab(path):
    d = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, quoting=3)
    d.columns = [c.lstrip("#") for c in d.columns]
    return d


def null_mask(s):
    return s.isin(NA)


def describe(values):
    s = pd.Series(values, dtype=float)
    return {k: round(float(v), 2) for k, v in s.describe(percentiles=[0.05, 0.5, 0.95]).items()}


# Mapping-readiness rules for screen metadata. These are heuristics, not vocabulary matches (Cellosaurus was not reachable).
GENERIC_CELL = re.compile(r"primary|patient|derived|organoid|ipsc|stem cell|\bcells?\b|tissue|mixed|pool", re.I)
CUSTOM_LIB = re.compile(r"custom|focused|targeted|sub-?pool|minipool|\(.*\d{4}\)|in-house", re.I)


def profile_index(idx):
    R = {"rows": len(idx), "columns": list(idx.columns)}
    R["null_rate"] = {c: round(float(null_mask(idx[c]).mean()), 4) for c in idx.columns}
    R["distinct"] = {c: int(idx[c].nunique()) for c in idx.columns}
    R["studies"] = int(idx["SOURCE_ID"].nunique())
    R["source_type"] = idx["SOURCE_TYPE"].value_counts().to_dict()
    for c in ["SCREEN_TYPE", "SCREEN_FORMAT", "EXPERIMENTAL_SETUP", "LIBRARY_TYPE", "LIBRARY_METHODOLOGY", "ENZYME",
              "THROUGHPUT", "PHENOTYPE", "SCORE_COL_COUNT", "FULL_SIZE_AVAILABLE", "ANALYSIS", "SIGNIFICANCE_INDICATOR"]:
        R.setdefault("top", {})[c] = idx[c].value_counts().head(30).to_dict()
    top = idx["SOURCE_ID"].value_counts().head(6)
    R["top_studies"] = [{"pubmed": s, "screens": int(n), "author": idx.loc[idx.SOURCE_ID == s, "AUTHOR"].iloc[0],
                         "analysis": idx.loc[idx.SOURCE_ID == s, "ANALYSIS"].iloc[0]} for s, n in top.items()]
    types = [f"SCORE.{i}_TYPE" for i in range(1, 6)]
    R["score_types_distinct"] = sorted({t for c in types for t in idx[c] if t not in NA})
    R["score1_type_top"] = idx["SCORE.1_TYPE"].value_counts().head(25).to_dict()
    R["score_type_any_position_screens"] = collections.Counter(
        t for r in idx[types].itertuples(index=False) for t in set(r) if t not in NA).most_common()
    return R


def profile_metadata(idx):
    """Per screen: is each of the four fields filled and plausibly mappable to a controlled term?"""
    n = len(idx)
    cl = idx["CELL_LINE"]
    cell_ok = ~null_mask(cl) & ~cl.str.contains(GENERIC_CELL)
    lib = idx["LIBRARY"]
    lib_ok = ~null_mask(lib) & ~lib.str.contains(CUSTOM_LIB)
    ph = idx["PHENOTYPE"]
    ph_ok = ~null_mask(ph)
    drug = idx["EXPERIMENTAL_SETUP"].eq("Drug Exposure")
    agent = ~null_mask(idx["CONDITION_NAME"])
    dose = ~null_mask(idx["CONDITION_DOSAGE"])
    # Treatment counts as mappable when the screen has no treatment, or names an agent.
    treat_ok = ~drug | agent
    all_ok = cell_ok & lib_ok & ph_ok & treat_ok
    pct = lambda m: round(100 * float(m.mean()), 1)
    return {
        "cell_line": {"filled_pct": pct(~null_mask(cl)), "named_line_pct": pct(cell_ok), "distinct": int(cl.nunique()),
                      "distinct_after_normalising": int(cl.str.lower().str.replace(r"[^a-z0-9]", "", regex=True).nunique()),
                      "generic_examples": cl[~cell_ok].value_counts().head(10).to_dict(),
                      "top10_share_pct": round(100 * cl.value_counts().head(10).sum() / n, 1)},
        "library": {"filled_pct": pct(~null_mask(lib)), "standard_named_pct": pct(lib_ok), "distinct": int(lib.nunique()),
                    "custom_examples": lib[~lib_ok].value_counts().head(8).to_dict(),
                    "top10_share_pct": round(100 * lib.value_counts().head(10).sum() / n, 1)},
        "phenotype": {"filled_pct": pct(ph_ok), "distinct": int(ph.nunique()), "values": ph.value_counts().to_dict()},
        "treatment": {"drug_exposure_screens": int(drug.sum()), "with_agent": int((drug & agent).sum()),
                      "with_dose": int((drug & dose).sum()), "distinct_agents": int(idx.loc[drug, "CONDITION_NAME"].nunique()),
                      "named_conditions_outside_drug_setup": int((~drug & agent).sum()),
                      "setup_values": idx["EXPERIMENTAL_SETUP"].value_counts().to_dict()},
        "all_four_mappable_pct": pct(all_ok),
        "all_four_mappable_screens": int(all_ok.sum()),
    }


def main(src, hgnc_path, ceg_path, neg_path, out_json, out_parquet=None):
    idx = read_tab(glob.glob(os.path.join(src, "*INDEX*"))[0]).set_index("SCREEN_ID", drop=False)
    R = {"index": profile_index(idx), "metadata": profile_metadata(idx)}

    hgnc = pd.read_csv(hgnc_path, sep="\t", dtype=str, keep_default_na=False)
    hgnc_entrez = dict(zip(hgnc["entrez_id"], hgnc["symbol"]))
    hgnc_entrez.pop("", None)
    ceg = set(pd.read_csv(ceg_path, sep="\t", dtype=str)["ENTREZ_ID"])
    neg = set(pd.read_csv(neg_path, sep="\t", dtype=str)["ENTREZ_ID"])

    files = sorted(glob.glob(os.path.join(src, "*.screen.tab.txt")))
    nulls, total = collections.Counter(), 0
    id_types, hit_vals = collections.Counter(), collections.Counter()
    per_screen, mismatches, direction = [], collections.Counter(), []
    dup_rows, dup_screens, nonnum = 0, 0, 0
    entrez_seen, entrez_not_hgnc, symbol_differs = set(), set(), set()
    columns = None
    parts = []
    for f in files:
        d = read_tab(f)
        columns = columns or list(d.columns)
        sid = d["SCREEN_ID"].iloc[0]
        m = idx.loc[sid]
        n = len(d)
        total += n
        for c in d.columns:
            nulls[c] += int(null_mask(d[c]).sum())
        id_types.update(d["IDENTIFIER_TYPE"])
        hit_vals.update(d["HIT"])
        used = [i for i in range(1, 6) if not null_mask(d[f"SCORE.{i}"]).all()]
        for i in used:
            v = d.loc[~null_mask(d[f"SCORE.{i}"]), f"SCORE.{i}"]
            nonnum += int(pd.to_numeric(v, errors="coerce").isna().sum())
        k = int(d.duplicated(["IDENTIFIER_ID"], keep=False).sum())
        dup_rows += k
        dup_screens += k > 0
        hits = int((d["HIT"] == "YES").sum())
        mismatches["scores_size"] += m["SCORES_SIZE"] not in NA and int(m["SCORES_SIZE"]) != n
        mismatches["number_of_hits"] += m["NUMBER_OF_HITS"] not in NA and int(m["NUMBER_OF_HITS"]) != hits
        mismatches["score_col_count"] += int(m["SCORE_COL_COUNT"]) != len(used)
        ent = d.loc[d.IDENTIFIER_TYPE == "ENTREZ_GENE", ["IDENTIFIER_ID", "OFFICIAL_SYMBOL"]].drop_duplicates()
        entrez_seen |= set(ent.IDENTIFIER_ID)
        entrez_not_hgnc |= set(ent.IDENTIFIER_ID) - hgnc_entrez.keys()
        symbol_differs |= {g for g, s in zip(ent.IDENTIFIER_ID, ent.OFFICIAL_SYMBOL) if g in hgnc_entrez and hgnc_entrez[g] != s}
        per_screen.append({"sid": sid, "rows": n, "hits": hits, "score_cols": len(used), "full": m["FULL_SIZE_AVAILABLE"]})
        # Known-biology direction: core essentials (CEGv2) vs non-essentials (NEGv1) on SCORE.1.
        s1 = pd.to_numeric(d["SCORE.1"], errors="coerce")
        in_ceg, in_neg = d.IDENTIFIER_ID.isin(ceg), d.IDENTIFIER_ID.isin(neg)
        if m["FULL_SIZE_AVAILABLE"] == "Yes" and in_ceg.sum() >= 50 and in_neg.sum() >= 50:
            direction.append({"type": m["SCORE.1_TYPE"], "screen_type": m["SCREEN_TYPE"],
                              "ceg_lower": float(s1[in_ceg].median()) < float(s1[in_neg].median())})
        if out_parquet:
            sc = {f"score_{i}": pd.to_numeric(d[f"SCORE.{i}"].where(~null_mask(d[f"SCORE.{i}"])), errors="coerce")
                  for i in range(1, 6)}
            parts.append(pd.DataFrame({"screen_id": d.SCREEN_ID.astype("int32"), "identifier_id": d.IDENTIFIER_ID,
                                       "identifier_type": d.IDENTIFIER_TYPE, "symbol": d.OFFICIAL_SYMBOL, **sc,
                                       "hit": d.HIT.eq("YES")}))

    ps = pd.DataFrame(per_screen)
    R["files"] = {"screen_files": len(files), "index_rows": len(idx), "result_columns": columns,
                  "screens_without_file": len(set(idx.index) - set(ps.sid)), "files_without_index_row": len(set(ps.sid) - set(idx.index))}
    R["results"] = {
        "total_rows": total, "rows_per_screen": describe(ps.rows), "hits_per_screen": describe(ps.hits),
        "screens_zero_hits": int((ps.hits == 0).sum()), "hit_only_screens": int((ps.full == "No").sum()),
        "rows_in_hit_only_screens": int(ps.loc[ps.full == "No", "rows"].sum()),
        "null_rate": {c: round(v / total, 4) for c, v in nulls.items()},
        "identifier_types": dict(id_types), "hit_values": dict(hit_vals), "nonnumeric_score_values": nonnum,
        "score_cols_used_per_screen": ps.score_cols.value_counts().sort_index().to_dict(),
        "duplicate_gene_rows": dup_rows, "screens_with_duplicate_genes": int(dup_screens),
        "index_mismatches": dict(mismatches),
    }
    R["genes"] = {"distinct_entrez": len(entrez_seen), "entrez_not_in_current_hgnc": len(entrez_not_hgnc),
                  "entrez_with_outdated_symbol": len(symbol_differs),
                  "examples_not_in_hgnc": sorted(entrez_not_hgnc)[:10]}
    dr = pd.DataFrame(direction)
    g = dr.groupby("type").agg(screens=("ceg_lower", "size"), ceg_lower_share=("ceg_lower", "mean"))
    R["direction"] = {"screens_tested": len(dr),
                      "by_score1_type": g.sort_values("screens", ascending=False).round(3).reset_index().to_dict("records")}

    if out_parquet:
        t = pd.concat(parts, ignore_index=True).sort_values(["identifier_id", "screen_id"])
        t.to_parquet(out_parquet, compression="zstd", index=False, row_group_size=500_000)
        R["parquet"] = {"rows": len(t), "bytes": os.path.getsize(out_parquet)}

    with open(out_json, "w") as fh:
        json.dump(R, fh, indent=1, default=str)
    print("rows", total, "screens", len(files))


if __name__ == "__main__":
    main(*sys.argv[1:])
