"""Cell line context: match ORCS cell line names to Cellosaurus, and through Cellosaurus to DepMap.

Pure functions only (tested in tests/test_context.py). Downloads and file output live in fetch_map.py.
A name is never guessed: a label that fits two cell lines is reported as ambiguous and left unmapped
until a person adds it to `overrides` in dataset.yaml.
"""
import re

FIELDS = ("accession", "name", "synonyms", "taxon", "depmap_id", "sanger_id", "sex", "category", "disease",
          "site", "problematic", "problem_note")


def parse_cellosaurus(lines):
    """Yield one dict per record of cellosaurus.txt (the header before the first ID line is skipped)."""
    rec = None
    for line in lines:
        line = line.rstrip("\n")
        tag, value = line[:2], line[5:].strip()
        if tag == "ID":
            rec = {"name": value, "accession": None, "synonyms": [], "taxon": None, "depmap_id": None,
                   "sanger_id": None, "sex": None, "category": None, "disease": None, "site": None,
                   "problematic": False, "problem_note": None}
        elif rec is None:
            continue
        elif line.startswith("//"):
            yield rec
            rec = None
        elif tag == "AC":
            rec["accession"] = value
        elif tag == "SY":
            rec["synonyms"] = [s.strip() for s in value.split(";") if s.strip()]
        elif tag == "OX" and rec["taxon"] is None:
            m = re.match(r"NCBI_TaxID=(\d+)", value)
            rec["taxon"] = m.group(1) if m else None
        elif tag == "DR":
            db, _, ident = value.partition(";")
            ident = ident.strip().split(";")[0].strip()
            if db == "DepMap" and rec["depmap_id"] is None:
                rec["depmap_id"] = ident
            elif db == "Cell_Model_Passport" and rec["sanger_id"] is None:
                rec["sanger_id"] = ident
        elif tag == "DI" and rec["disease"] is None:
            parts = [p.strip() for p in value.split(";")]
            rec["disease"] = parts[2] if len(parts) > 2 else parts[-1]
        elif tag == "SX":
            rec["sex"] = value
        elif tag == "CA":
            rec["category"] = value
        elif tag == "CC" and value.startswith("Problematic cell line:"):
            rec["problematic"], rec["problem_note"] = True, value.split(":", 1)[1].strip()
        elif tag == "CC" and value.startswith("Derived from site:") and rec["site"] is None:
            parts = [p.strip() for p in value.split(":", 1)[1].split(";")]
            rec["site"] = parts[1] if len(parts) > 1 else parts[0]


def normalize(name):
    """Upper case, letters and digits only: 'MDA-MB-231', 'mda mb 231' -> 'MDAMB231'."""
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def build_index(records, taxon="9606"):
    """Lookup tables for one species: exact name, exact synonym, normalized name-or-synonym -> accessions."""
    index = {"name": {}, "synonym": {}, "normalized": {}, "records": {}}
    for r in records:
        if r["taxon"] != taxon or not r["accession"]:
            continue
        index["records"][r["accession"]] = r
        index["name"].setdefault(r["name"].upper(), set()).add(r["accession"])
        for s in r["synonyms"]:
            index["synonym"].setdefault(s.upper(), set()).add(r["accession"])
        for s in [r["name"], *r["synonyms"]]:
            index["normalized"].setdefault(normalize(s), set()).add(r["accession"])
    return index


def match(label, index, overrides=None):
    """Return (accession or None, method, note). Steps: manual override, exact name, exact synonym, normalized."""
    if overrides and label in overrides:
        ac = overrides[label]
        if ac not in index["records"]:
            raise ValueError(f"override for {label!r} points to unknown accession {ac!r}")
        return ac, "manual", ""
    for method, key in (("exact_name", label.upper()), ("synonym", label.upper()),
                        ("normalized_name", normalize(label))):
        table = index["name" if method == "exact_name" else "synonym" if method == "synonym" else "normalized"]
        hits = table.get(key, set())
        if len(hits) == 1:
            return next(iter(hits)), method, ""
        if len(hits) > 1:
            names = ", ".join(f"{a} ({index['records'][a]['name']})" for a in sorted(hits))
            return None, "ambiguous", f"{method} fits {names}"
    return None, "not_found", ""


def map_screens(screens, index, overrides=None):
    """One output row per screen (none dropped) plus a coverage summary."""
    cache, rows = {}, []
    for s in screens:
        label = s.get("cell_line_label")
        if not label:
            ac, method, note = None, "missing_label", ""
        else:
            if label not in cache:
                cache[label] = match(label, index, overrides)
            ac, method, note = cache[label]
        rec = index["records"].get(ac, {}) if ac else {}
        rows.append({"screen_id": s["screen_id"], "cell_line_label": label, "cellosaurus_id": ac, "method": method,
                     "note": note, "cellosaurus_name": rec.get("name"), "depmap_id": rec.get("depmap_id"),
                     "sanger_id": rec.get("sanger_id"), "problematic": rec.get("problematic")})
    labels = {r["cell_line_label"] for r in rows if r["cell_line_label"]}
    by_method = {}
    for r in rows:
        by_method[r["method"]] = by_method.get(r["method"], 0) + 1
    summary = {
        "screens": len(rows), "screens_mapped": sum(r["cellosaurus_id"] is not None for r in rows),
        "lines": len(labels), "lines_mapped": sum(cache[label][0] is not None for label in labels),
        "screens_with_depmap": sum(bool(r["depmap_id"]) for r in rows),
        "lines_with_depmap": len({r["cellosaurus_id"] for r in rows if r["depmap_id"]}),
        "screens_problematic": sum(bool(r["problematic"]) for r in rows),
        "by_method": by_method,
    }
    return rows, summary


def pick_depmap_files(listing, wanted, release_pattern=r"^DepMap Public"):
    """From the DepMap download listing, take the newest matching release and find one file per wanted pattern.

    Returns (release name, {key: listing row}, [keys not found])."""
    rel = [r for r in listing if re.search(release_pattern, r.get("release", ""))]
    if not rel:
        return None, {}, sorted(wanted)
    latest = max(rel, key=lambda r: (r.get("release_date", ""), r["release"]))["release"]
    files, missing = {}, []
    for key, pattern in wanted.items():
        hits = [r for r in rel if r["release"] == latest and re.search(pattern, r.get("filename", ""))]
        if hits:
            files[key] = hits[0]
        else:
            missing.append(key)
    return latest, files, sorted(missing)


def figshare_listing(articles, files_by_article, title_pattern):
    """Turn figshare articles (DepMap mirrors each public release there) into download-listing rows."""
    rows = []
    for a in articles:
        if not re.search(title_pattern, a.get("title", "")):
            continue
        for f in files_by_article.get(a["id"], []):
            rows.append({"release": a["title"], "release_date": (a.get("published_date") or "")[:10],
                         "filename": f["name"], "url": f["download_url"], "size": str(f.get("size", "")),
                         "md5": f.get("computed_md5", ""), "licence": (a.get("license") or {}).get("name", "")})
    return rows
