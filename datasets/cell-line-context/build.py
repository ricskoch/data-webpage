"""Step 2 of the cell line context data (M3b): build the cell line tables for the screened lines.

Usage: python3 -I build.py <work_dir>   (after fetch_map.py has written <work_dir>/out/)
Reads the DepMap release files listed in out/depmap_files.csv, keeps only the cell lines that ORCS screened,
and writes:
  out/context/*.parquet   cell_lines, screen_cell_lines, mutations, expression, copy_number
  out/context/build_report.md
  site/ctx/lines.json      one entry per cell line (context card) + screen -> line index
  site/ctx/g/NNNN.json     per gene: expression, copy number and mutations aligned to lines.json order
Nothing is coerced silently: missing values stay missing, and every filter is counted in the report.
"""
import csv
import json
import math
import pathlib
import re
import sys

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "biogrid-orcs"))
import fetch_map  # noqa: E402
from export_site import shard_of  # noqa: E402  (same gene shards as the ORCS lookup)

GENE_COL = re.compile(r"^(\S+) \((\d+)\)$")
MUT_COLUMNS = {  # our name -> accepted DepMap column names, first match wins
    "depmap_id": ["ModelID"], "symbol": ["HugoSymbol"], "entrez": ["EntrezGeneID"],
    "protein_change": ["ProteinChange"], "impact": ["VepImpact"],
    "likely_lof": ["LikelyLoF"], "hotspot": ["Hotspot"],
}
REQUIRED_MUT = ("depmap_id", "symbol", "protein_change")
SIGNATURES = {"Ploidy": "ploidy", "WGD": "wgd", "MSIScore": "msi_score", "Aneuploidy": "aneuploidy",
              "CIN": "cin", "LoHFraction": "loh_fraction"}
MODEL_FIELDS = {"OncotreeLineage": "lineage", "OncotreePrimaryDisease": "disease", "OncotreeSubtype": "subtype",
                "Sex": "sex", "Age": "age", "PrimaryOrMetastasis": "primary_or_metastasis"}


def parse_gene_column(name):
    """'TP53 (7157)' -> ('TP53', 7157); anything else -> None."""
    m = GENE_COL.match(str(name))
    return (m.group(1), int(m.group(2))) if m else None


def read_matrix(fh, wanted, chunksize=200):
    """Read a DepMap model x gene CSV in chunks, keep wanted models, return long rows (depmap_id, entrez, value)."""
    parts, info = [], {"models_read": 0, "models_kept": 0, "ignored_columns": []}
    for chunk in pd.read_csv(fh, chunksize=chunksize, low_memory=False):
        if "IsDefaultEntryForModel" in chunk.columns:
            chunk = chunk[chunk["IsDefaultEntryForModel"].astype(str).str.lower().isin(["yes", "true"])]
        idcol = "ModelID" if "ModelID" in chunk.columns else chunk.columns[0]
        genes = {c: parse_gene_column(c) for c in chunk.columns if parse_gene_column(c)}
        if not info["ignored_columns"]:
            info["ignored_columns"] = [c for c in chunk.columns if c not in genes and c != idcol and
                                       c not in ("SequencingID", "ProfileID", "IsDefaultEntryForModel",
                                                 "ModelConditionID", "IsDefaultEntryForMC")]
        info["models_read"] += len(chunk)
        chunk = chunk[chunk[idcol].isin(wanted)]
        info["models_kept"] += len(chunk)
        if chunk.empty:
            continue
        long = chunk[[idcol, *genes]].melt(id_vars=idcol, var_name="column", value_name="value")
        long["entrez"] = long["column"].map(lambda c: genes[c][1])
        parts.append(long.rename(columns={idcol: "depmap_id"})[["depmap_id", "entrez", "value"]])
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["depmap_id", "entrez", "value"])
    out["value"] = out["value"].astype("float32")
    return out, info


def select_mutations(df, wanted):
    """Protein-altering mutations of the wanted models, with DepMap's driver flags kept as they are."""
    cols = {ours: next((c for c in names if c in df.columns), None) for ours, names in MUT_COLUMNS.items()}
    missing = [k for k in REQUIRED_MUT if cols[k] is None]
    if missing:
        raise KeyError(f"mutation file lacks required columns for {missing}; has {list(df.columns)[:30]}")
    out = pd.DataFrame({k: df[c] if c else None for k, c in cols.items()})
    info = {"rows_read": len(out)}
    mine = out["depmap_id"].isin(wanted)
    info["other_models"] = int((~mine).sum())
    out = out[mine]
    change = out["protein_change"].fillna("").astype(str).str.strip()
    altering = change.ne("") & ~change.str.endswith("=")  # synonymous changes (p.X100=) do not alter the protein
    if cols["impact"]:
        altering &= out["impact"].isin(["HIGH", "MODERATE"])
    info["not_protein_altering"] = int((~altering).sum())
    out = out[altering].copy()
    for flag in ("likely_lof", "hotspot"):
        out[flag] = out[flag].map(lambda v: str(v).lower() in ("true", "1", "yes")) if cols[flag] else False
    out["entrez"] = pd.to_numeric(out["entrez"], errors="coerce").astype("Int64")
    info["kept"] = len(out)
    return out.reset_index(drop=True), info


def models_with_calls(df, wanted):
    """Wanted models that appear in the mutation file at all. A line missing here has no mutation calls, so it
    must not be counted as wild-type for any gene."""
    col = next(c for c in MUT_COLUMNS["depmap_id"] if c in df.columns)
    return set(df[col].dropna()) & set(wanted)


def line_table(mapping, models, signatures):
    """One row per screened cell line that DepMap profiles, joined by Cellosaurus ID (DepMap's RRID column)."""
    m = mapping.dropna(subset=["cellosaurus_id"])
    counts = m.groupby("cellosaurus_id").agg(screens=("screen_id", "size"), name=("cellosaurus_name", "first"),
                                             problematic=("problematic", "first")).reset_index()
    mod = models.rename(columns={"ModelID": "depmap_id", "RRID": "cellosaurus_id", **MODEL_FIELDS})
    keep = ["depmap_id", "cellosaurus_id", *[v for k, v in MODEL_FIELDS.items() if k in models.columns]]
    lines = counts.merge(mod[keep].dropna(subset=["cellosaurus_id"]), on="cellosaurus_id", how="inner")
    sig = signatures.rename(columns={"ModelID": "depmap_id", **SIGNATURES})
    lines = lines.merge(sig[["depmap_id", *[v for k, v in SIGNATURES.items() if k in signatures.columns]]],
                        on="depmap_id", how="left")
    return lines.sort_values(["lineage", "name"] if "lineage" in lines else ["name"]).reset_index(drop=True)


def num(x, digits=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x) else round(float(x), digits)


def pack_gene(entrez, order, expr, cn, muts):
    """Per-gene arrays aligned to the line order: e = expression, c = copy number, m = [line, change, lof, hotspot]."""
    pos = {d: i for i, d in enumerate(order)}
    e, c = [None] * len(order), [None] * len(order)
    for d, v in zip(expr["depmap_id"], expr["value"]):
        if d in pos:
            e[pos[d]] = num(v)
    for d, v in zip(cn["depmap_id"], cn["value"]):
        if d in pos:
            c[pos[d]] = num(v)
    m = [[pos[d], str(p), int(bool(lof)), int(bool(h))] for d, p, lof, h in
         zip(muts["depmap_id"], muts["protein_change"], muts["likely_lof"], muts["hotspot"]) if d in pos]
    return {"e": e, "c": c, "m": sorted(m)}


def drivers(muts, panel):
    """Per line: the panel genes it carries a protein-altering mutation in, e.g. 'TP53 p.R175H'."""
    hit = muts[muts["symbol"].isin(panel)]
    return {d: sorted(f"{s} {p}" for s, p in zip(g["symbol"], g["protein_change"]))
            for d, g in hit.groupby("depmap_id")}


def driver_classes(muts, panel):
    """Per line: the panel genes with a loss-of-function mutation (DepMap LikelyLoF) and with a gain-of-function-like
    one (DepMap Hotspot, not LikelyLoF). A gene can be in both lists; a passenger missense is in neither."""
    hit = muts[muts["symbol"].isin(panel)]
    out = {}
    for d, g in hit.groupby("depmap_id"):
        lof = g["likely_lof"].astype(bool)
        gof = g["hotspot"].astype(bool) & ~lof
        out[d] = {"lof": sorted(set(g.loc[lof, "symbol"])), "gof": sorted(set(g.loc[gof, "symbol"]))}
    return out


def main(work):
    out, ctx, site = work / "out", work / "out" / "context", work / "site" / "ctx"
    (site / "g").mkdir(parents=True, exist_ok=True)
    ctx.mkdir(parents=True, exist_ok=True)
    cfg = fetch_map.CONFIG["build"]
    with open(out / "depmap_files.csv") as f:
        listing = list(csv.DictReader(f))
    _, files, missing = fetch_map.context.pick_depmap_files(
        listing, fetch_map.CONFIG["sources"]["depmap"]["files"], r".")
    need = {"models", "signatures", "mutations", "expression", "copy_number"}
    if need - set(files):
        raise SystemExit(f"DepMap release lacks {sorted(need - set(files))}")
    local = {}
    for key in need:
        local[key] = work / files[key]["filename"]
        fetch_map.get(files[key]["url"], local[key])

    mapping = pd.read_csv(out / "screen_cell_lines.csv", dtype=str)
    mapping["problematic"] = mapping["problematic"].map({"True": True, "False": False})
    lines = line_table(mapping, pd.read_csv(local["models"], dtype=str),
                       pd.read_csv(local["signatures"]).rename(columns={"Unnamed: 0": "ModelID"}))
    wanted = set(lines["depmap_id"])
    report = ["# Cell line context: build report", "", f"- Cell lines with DepMap data: {len(lines):,}"]

    header = pd.read_csv(local["mutations"], nrows=0).columns
    usecols = [c for names in MUT_COLUMNS.values() for c in names if c in header]
    raw = pd.read_csv(local["mutations"], usecols=usecols, low_memory=False)
    muts, minfo = select_mutations(raw, wanted)
    lines["mutation_calls"] = lines["depmap_id"].isin(models_with_calls(raw, wanted))
    report.append(f"- Mutations: {minfo}; lines without any mutation calls: {int((~lines['mutation_calls']).sum())}")
    expr, einfo = read_matrix(local["expression"], wanted)
    report.append(f"- Expression: {einfo['models_kept']} of {einfo['models_read']} models kept; "
                  f"{expr['entrez'].nunique():,} genes; median log2(TPM+1) {expr['value'].median():.2f}; "
                  f"ignored columns {einfo['ignored_columns'][:10]}")
    cn, cinfo = read_matrix(local["copy_number"], wanted)
    report.append(f"- Copy number: {cinfo['models_kept']} of {cinfo['models_read']} models kept; "
                  f"{cn['entrez'].nunique():,} genes; median value {cn['value'].median():.2f} "
                  f"(expected about 1 for a normal two-copy gene if the unit is log2(ratio + 1))")
    no_expr = sorted(wanted - set(expr["depmap_id"]))
    report.append(f"- Lines without expression data: {len(no_expr)}; without copy number: "
                  f"{len(wanted - set(cn['depmap_id']))}")

    drv = drivers(muts, set(cfg["driver_panel"]))
    lines["drivers"] = lines["depmap_id"].map(lambda d: drv.get(d, []))
    cls = driver_classes(muts, set(cfg["driver_panel"]))
    lines["drivers_lof"] = lines["depmap_id"].map(lambda d: cls.get(d, {}).get("lof", []))
    lines["drivers_gof"] = lines["depmap_id"].map(lambda d: cls.get(d, {}).get("gof", []))
    order = lines["depmap_id"].tolist()
    by_line = {c: i for i, c in enumerate(lines["cellosaurus_id"])}
    screen_line = {s: by_line[c] for s, c in zip(mapping["screen_id"], mapping["cellosaurus_id"]) if c in by_line}
    records = json.loads(lines.astype(object).where(lines.notna(), None).to_json(orient="records"))
    (site / "lines.json").write_text(json.dumps({"release": files["models"].get("release"), "lines": records,
                                                 "screen_line": screen_line}, separators=(",", ":")))
    report.append(f"- Screens linked to a line with DepMap data: {len(screen_line):,}")

    for name, df in (("cell_lines", lines.astype({"drivers": str, "drivers_lof": str, "drivers_gof": str})), ("screen_cell_lines", mapping),
                     ("mutations", muts), ("expression", expr), ("copy_number", cn)):
        df.to_parquet(ctx / f"{name}.parquet", index=False)

    shards = {}
    eg, cg, mg = (dict(tuple(d.groupby("entrez"))) for d in (expr, cn, muts.dropna(subset=["entrez"])))
    empty_m = muts.iloc[0:0]
    for entrez in sorted(set(eg) | set(cg) | set(mg)):
        pid = f"entrez:{int(entrez)}"
        shards.setdefault(shard_of(pid), {})[pid] = pack_gene(
            entrez, order, eg.get(entrez, expr.iloc[0:0]), cg.get(entrez, cn.iloc[0:0]), mg.get(entrez, empty_m))
    for n, part in shards.items():
        (site / "g" / f"{n:04d}.json").write_text(json.dumps(part, separators=(",", ":")))
    report.append(f"- Gene shards: {len(shards)} files, {sum(len(p) for p in shards.values()):,} genes")
    text = "\n".join(report) + "\n"
    (ctx / "build_report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
