"""Drug label -> identifiers (F20, drug plan step 2). Pure functions; the network call is passed in.

ORCS writes the condition as free text: "Olaparib", "Mutation: BRCA2 KO | Olaparib", sometimes two drugs. This module
splits a label into a genetic background and drug components, and looks each component up by name in PubChem
(compound ID, CID) and ChEMBL (ID). Nothing is guessed: a name with no match is reported "unmapped"; a name with several
PubChem matches is reported "review" (the first CID is kept as a suggestion); ChEMBL is accepted only on an exact
preferred-name match. The output is a draft for a person to review before it becomes `drugs.yaml`.
"""
import concurrent.futures
import re
import urllib.parse

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json"
BACKGROUND = re.compile(r"^(mutation|knockout|knock-out|ko|deletion|overexpression)\s*:", re.I)
# Conditions that are organisms or cells, not compounds: not looked up, reported as "not_a_compound".
NOT_COMPOUND = re.compile(r"\b(virus|viral|bacteri\w*|phage|t3ss\w*|[a-z]+ cells?)\b|^virus\s*:", re.I)
DOSE_LIKE = re.compile(r"^[\d.,\s]*\d\s*[a-zµ]*(/[a-z]+)?$", re.I)
PARENS = re.compile(r"\(([^()]*)\)")


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def split_outside_brackets(text):
    """Split on ' + ' that is not inside brackets ("Immunotherapy (GVAX + PD-1 blockade)" is one treatment)."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        depth += (ch == "(") - (ch == ")" and depth > 0)
        if depth == 0 and text[i:i + 3] == " + ":
            parts.append(text[start:i])
            start = i + 3
    return parts + [text[start:]]


def split_label(label):
    """{'background': [...], 'components': [...]}. Parts are split on '|' and ' + '; background parts start 'Mutation:' etc."""
    background, components = [], []
    for part in str(label).split("|"):
        part = norm(part)
        if not part:
            continue
        if BACKGROUND.match(part):
            background.append(part)
        else:
            components += [c for c in (norm(c) for c in split_outside_brackets(part)) if c]
    return {"background": background, "components": components}


def pubchem_cids(name, fetch_json):
    data = fetch_json(f"{PUBCHEM}/name/{urllib.parse.quote(name, safe='')}/cids/JSON")
    return (data or {}).get("IdentifierList", {}).get("CID", [])


def pubchem_title(cid, fetch_json):
    data = fetch_json(f"{PUBCHEM}/cid/{cid}/property/Title/JSON")
    props = (data or {}).get("PropertyTable", {}).get("Properties", [])
    return props[0].get("Title") if props else None


def chembl_exact(name, fetch_json):
    data = fetch_json(f"{CHEMBL}?q={urllib.parse.quote(name, safe='')}&limit=5")
    for m in (data or {}).get("molecules", []):
        if (m.get("pref_name") or "").casefold() == name.casefold():
            return m["molecule_chembl_id"]
    return None


def candidates(name):
    """Spellings to try, best first: the name without brackets, then each bracketed alias that is not a dose, then as written."""
    bare = norm(PARENS.sub("", name))
    aliases = [norm(a) for a in PARENS.findall(name) if norm(a) and not DOSE_LIKE.match(norm(a))]
    seen, out = set(), []
    for c in [bare, *aliases, name]:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def load_curated(path):
    """{name as written: {canonical, kind, confidence, note}} from the reviewed drugs.yaml."""
    import yaml
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("curated", {})


def worst(statuses):
    return next(s for s in ("unmapped", "review", "mapped") if s in statuses)


def resolve_curated(name, entry, fetch_json):
    """A person has reviewed this name: look up the reviewed spelling(s) only. No canonical = no identifier expected."""
    out = {"name": name, "status": "no_id", "pubchem_cid": None, "pubchem_title": None, "chembl_id": None,
           "looked_up_as": None, "curated": True, "kind": entry["kind"], "confidence": entry["confidence"]}
    canonical = entry.get("canonical")
    if canonical is None:
        return out
    names = canonical if isinstance(canonical, list) else [canonical]
    found = [resolve_spelling(n, fetch_json) for n in names]
    out.update({k: found[0][k] for k in ("pubchem_cid", "pubchem_title", "chembl_id", "looked_up_as")})
    out["status"] = worst({f["status"] for f in found})
    if len(found) > 1:
        out["compounds"] = found
    return out


def resolve_spelling(spelling, fetch_json):
    out = {"status": "unmapped", "pubchem_cid": None, "pubchem_title": None, "chembl_id": None, "looked_up_as": spelling}
    cids = pubchem_cids(spelling, fetch_json)
    if cids:
        out.update(status="mapped" if len(cids) == 1 else "review", pubchem_cid=cids[0],
                   pubchem_title=pubchem_title(cids[0], fetch_json))
    out["chembl_id"] = chembl_exact(spelling, fetch_json)
    return out


def resolve(name, fetch_json, curated=None):
    if curated and name in curated:
        return resolve_curated(name, curated[name], fetch_json)
    out = {"name": name, "status": "unmapped", "pubchem_cid": None, "pubchem_title": None, "chembl_id": None,
           "looked_up_as": None}
    if NOT_COMPOUND.search(name):
        out["status"] = "not_a_compound"
        return out
    for spelling in candidates(name):
        cids = pubchem_cids(spelling, fetch_json)
        if cids:
            out.update(status="mapped" if len(cids) == 1 else "review", pubchem_cid=cids[0], looked_up_as=spelling,
                       pubchem_title=pubchem_title(cids[0], fetch_json))
            break
    for spelling in candidates(name):
        out["chembl_id"] = chembl_exact(spelling, fetch_json)
        if out["chembl_id"]:
            break
    return out


def build_mapping(labels, fetch_json, workers=1, progress=None, curated=None):
    """{label: {background, components: [resolved...]}} for each distinct label; each distinct drug name is looked up once.

    workers > 1 looks names up in parallel (the caller's fetch_json must keep to the services' rate limits);
    progress(done, total, name) is called after each name."""
    parts = {label: split_label(label) for label in sorted(set(labels))}
    names = sorted({n for p in parts.values() for n in p["components"]})
    resolved = {}

    def one(name):
        return name, resolve(name, fetch_json, curated)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for k, (name, r) in enumerate(pool.map(one, names), 1):
            resolved[name] = r
            if progress:
                progress(k, len(names), name)
    return {label: {"background": p["background"], "components": [resolved[n] for n in p["components"]]}
            for label, p in parts.items()}


def summary(mapping):
    """Counts of labels by their worst compound status (no components = 'background_only'; only organisms/cells = 'not_a_compound')."""
    order = ["unmapped", "review", "mapped"]
    counts = {"mapped": 0, "review": 0, "unmapped": 0, "not_a_compound": 0, "no_id": 0, "background_only": 0}
    for entry in mapping.values():
        states = {c["status"] for c in entry["components"]}
        compounds = states - {"not_a_compound", "no_id"}
        if not states:
            counts["background_only"] += 1
        elif not compounds:
            counts["no_id" if "no_id" in states else "not_a_compound"] += 1
        else:
            counts[next(s for s in order if s in compounds)] += 1
    return counts
