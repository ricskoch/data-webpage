"""BioGRID ORCS adapter: source files -> unified model tables (spec section 12.2). Pure functions, no I/O beyond
reading the file handle given. Nothing is dropped or silently coerced: a row that cannot be parsed goes to the
rejected table with a reason, and source_row keeps every row traceable to its line in the source file."""
import re

import numpy as np
import pandas as pd

SCREEN_PREFIX = "biogrid-orcs:"
N_SCORES = 5


class SchemaError(ValueError):
    pass


def read_tab(handle):
    """Read a BioGRID tab file as text. '#' is stripped from the first header name; values are not converted."""
    d = pd.read_csv(handle, sep="\t", dtype=str, keep_default_na=False, quoting=3)
    d.columns = [c.lstrip("#") for c in d.columns]
    return d


def missing(series, na="-"):
    return series.isin([na, ""])


def parse_scores(raw, na="-"):
    """Text scores -> float. Returns (values, bad) where bad marks text that is neither missing nor a number."""
    values = pd.to_numeric(raw.where(~missing(raw, na)), errors="coerce")
    bad = ~missing(raw, na) & values.isna()
    return values, bad


def classify_identifier(itype, ident, symbol, config):
    """Return (gene_id, gene_id_status, perturbation_id). Non-Entrez rows keep a null gene_id and a reason as status."""
    entrez = itype.eq("ENTREZ_GENE") & ident.str.fullmatch(r"\d+")
    gene_id = pd.array(np.where(entrez, ident, None), dtype="Int64") if len(ident) else pd.array([], dtype="Int64")
    status = itype.map(config["mappings"]["unresolved_identifier"]).where(~entrez)
    status = status.fillna("unknown_identifier").where(~entrez)
    pattern = re.compile("|".join(config["mappings"]["control_symbol_patterns"]), re.I)
    status = status.mask(~entrez & symbol.str.contains(pattern), "control").fillna("entrez")
    pid = np.where(entrez, "entrez:" + ident, "orcs:" + ident)
    return gene_id, status, pid


def parse_screen_file(handle, screen_id, config):
    """One per-screen file -> (results, rejected). source_row is the line number in the file (header = line 1)."""
    d = read_tab(handle)
    if list(d.columns) != config["expected_columns"]["screen"]:
        raise SchemaError(f"screen {screen_id}: unexpected columns {list(d.columns)}")
    na = config["source"]["missing_value"]
    d.insert(0, "source_row", np.arange(2, len(d) + 2, dtype="int32"))
    reason = pd.Series(None, index=d.index, dtype=object)
    scores = {}
    for k in range(1, N_SCORES + 1):
        scores[k], bad = parse_scores(d[f"SCORE.{k}"], na)
        reason = reason.mask(reason.isna() & bad, f"score_{k}_not_numeric")
    reason = reason.mask(reason.isna() & ~d["HIT"].isin(["YES", "NO"]), "hit_not_yes_no")
    reason = reason.mask(reason.isna() & d["ORGANISM_ID"].ne(config["organism_id"]), "organism_not_9606")
    reason = reason.mask(reason.isna() & d["SCREEN_ID"].ne(screen_id), "screen_id_mismatch")

    ok = reason.isna()
    rejected = d[~ok].assign(screen_id=SCREEN_PREFIX + screen_id, reason=reason[~ok]).reset_index(drop=True)
    g = d[ok]
    gene_id, status, pid = classify_identifier(g["IDENTIFIER_TYPE"], g["IDENTIFIER_ID"], g["OFFICIAL_SYMBOL"], config)
    results = pd.DataFrame({
        "screen_id": SCREEN_PREFIX + screen_id,
        "perturbation_id": pid,
        "gene_id": gene_id,
        "gene_id_status": status.values,
        "source_identifier": g["IDENTIFIER_ID"].values,
        "symbol": g["OFFICIAL_SYMBOL"].values,
        **{f"score_{k}": scores[k][ok].values for k in scores},
        "hit_source": g["HIT"].eq("YES").values,
        "source_row": g["source_row"].values,
    })
    return results, rejected


def _map(series, mapping):
    return series.map(mapping).fillna("unmapped")


def to_screens(index, config):
    """Index rows -> screens table. Values without a mapping in dataset.yaml become 'unmapped', never guessed."""
    m = config["mappings"]
    na = config["source"]["missing_value"]
    text = lambda c: index[c].where(~missing(index[c], na), None)
    return pd.DataFrame({
        "screen_id": SCREEN_PREFIX + index["SCREEN_ID"],
        "source_screen_id": index["SCREEN_ID"],
        "source_dataset": config["id"],
        "study_id": index["SOURCE_TYPE"] + ":" + index["SOURCE_ID"],
        "organism": "human",
        "cell_line_label": index["CELL_LINE"],
        "cell_type_label": text("CELL_TYPE"),
        "library_name": index["LIBRARY"],
        "library_type": index["LIBRARY_TYPE"],
        "perturbation_type": _map(index["LIBRARY_TYPE"], m["perturbation_type"]),
        "cas_system": index["ENZYME"],
        "screen_format": "monogenic",
        "screen_layout": index["SCREEN_FORMAT"],
        "experimental_setup": index["EXPERIMENTAL_SETUP"],
        "phenotype": index["PHENOTYPE"],
        "selection_type": _map(index["SCREEN_TYPE"], m["selection_type"]),
        "timepoint": text("DURATION"),
        "scoring_method": index["ANALYSIS"],
        "hit_rule_source": text("SIGNIFICANCE_CRITERIA"),
        "result_scope": _map(index["FULL_SIZE_AVAILABLE"], m["result_scope"]),
        "score_col_count": index["SCORE_COL_COUNT"].astype(int),
        "expected_rows": index["SCORES_SIZE"].astype(int),
        "expected_hits": index["NUMBER_OF_HITS"].astype(int),
    })


def to_studies(index, config):
    first = index.drop_duplicates(["SOURCE_TYPE", "SOURCE_ID"])
    return pd.DataFrame({
        "study_id": first["SOURCE_TYPE"] + ":" + first["SOURCE_ID"],
        "pubmed_id": first["SOURCE_ID"].where(first["SOURCE_TYPE"].eq("pubmed"), None),
        "author_label": first["AUTHOR"],
        "year": first["AUTHOR"].str.extract(r"\((\d{4})\)")[0].astype("Int64"),
        "source_dataset": config["id"],
        "source_release": config["source"]["release"],
        "licence_id": config["licence"]["id"],
    }).reset_index(drop=True)


def to_score_defs(index):
    """One row per native score column. method_family and direction are added in the normalization step."""
    rows = [{"screen_id": SCREEN_PREFIX + r["SCREEN_ID"], "position": k, "native_name": r[f"SCORE.{k}_TYPE"]}
            for _, r in index.iterrows() for k in range(1, N_SCORES + 1) if r[f"SCORE.{k}_TYPE"] not in ("-", "")]
    return pd.DataFrame(rows, columns=["screen_id", "position", "native_name"])


DOSE = re.compile(r"^\s*([0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*([^\d\s].*?)\s*$")


def to_conditions(index):
    """Screens naming a condition get one treatment row. Dose is split only when it is 'number unit'."""
    has = ~missing(index["CONDITION_NAME"])
    rows = []
    for _, r in index[has].iterrows():
        raw = None if r["CONDITION_DOSAGE"] in ("-", "") else r["CONDITION_DOSAGE"]
        m = DOSE.match(raw) if raw else None
        rows.append({"condition_id": f"{SCREEN_PREFIX}{r['SCREEN_ID']}:1", "screen_id": SCREEN_PREFIX + r["SCREEN_ID"],
                     "role": "treatment", "agent_label": r["CONDITION_NAME"], "setup": r["EXPERIMENTAL_SETUP"],
                     "dose": float(m.group(1)) if m else np.nan, "dose_unit": m.group(2) if m else None,
                     "dose_raw": raw, "duration": None if r["DURATION"] in ("-", "") else r["DURATION"]})
    return pd.DataFrame(rows, columns=["condition_id", "screen_id", "role", "agent_label", "setup", "dose",
                                       "dose_unit", "dose_raw", "duration"])


def check_screen_counts(screens, results, rejected):
    """Rows (kept + rejected) and hits per screen must equal the index. Returns a list of problems (empty = pass)."""
    kept = results.groupby("screen_id").agg(rows=("source_row", "size"), hits=("hit_source", "sum"))
    rej = rejected.groupby("screen_id").agg(rows=("source_row", "size"), hits=("HIT", lambda h: h.eq("YES").sum())) \
        if len(rejected) else pd.DataFrame(columns=["rows", "hits"])
    got = kept.add(rej, fill_value=0)
    problems = []
    for s in screens.itertuples():
        rows = int(got["rows"].get(s.screen_id, 0))
        hits = int(got["hits"].get(s.screen_id, 0))
        if rows != s.expected_rows:
            problems.append({"screen_id": s.screen_id, "check": "row_count", "expected": s.expected_rows, "got": rows})
        if hits != s.expected_hits:
            problems.append({"screen_id": s.screen_id, "check": "hit_count", "expected": s.expected_hits, "got": hits})
    return problems
