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


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


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
            components += [c for c in (norm(c) for c in re.split(r"\s\+\s", part)) if c]
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


def resolve(name, fetch_json):
    cids = pubchem_cids(name, fetch_json)
    out = {"name": name, "status": "unmapped", "pubchem_cid": None, "pubchem_title": None, "chembl_id": None}
    if cids:
        out.update(status="mapped" if len(cids) == 1 else "review", pubchem_cid=cids[0],
                   pubchem_title=pubchem_title(cids[0], fetch_json))
    out["chembl_id"] = chembl_exact(name, fetch_json)
    return out


def build_mapping(labels, fetch_json, workers=1, progress=None):
    """{label: {background, components: [resolved...]}} for each distinct label; each distinct drug name is looked up once.

    workers > 1 looks names up in parallel (the caller's fetch_json must keep to the services' rate limits);
    progress(done, total, name) is called after each name."""
    parts = {label: split_label(label) for label in sorted(set(labels))}
    names = sorted({n for p in parts.values() for n in p["components"]})
    resolved = {}

    def one(name):
        return name, resolve(name, fetch_json)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for k, (name, r) in enumerate(pool.map(one, names), 1):
            resolved[name] = r
            if progress:
                progress(k, len(names), name)
    return {label: {"background": p["background"], "components": [resolved[n] for n in p["components"]]}
            for label, p in parts.items()}


def summary(mapping):
    """Counts of labels by their worst component status (no components = 'background_only')."""
    order = ["unmapped", "review", "mapped"]
    counts = {"mapped": 0, "review": 0, "unmapped": 0, "background_only": 0}
    for entry in mapping.values():
        states = {c["status"] for c in entry["components"]}
        counts["background_only" if not states else next(s for s in order if s in states)] += 1
    return counts
