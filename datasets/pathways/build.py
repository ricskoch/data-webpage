"""Reactome pathways for the gene picker: download the human GMT file, check it, write pathways.json.

Usage: python3 -I build.py <work_dir>
Writes <work_dir>/site/pathways.json (what the site loads), <work_dir>/out/rejects.csv (lines not used, with reasons)
and <work_dir>/out/report.md (counts and the licence evidence). Standard library only.
"""
import csv
import io
import json
import pathlib
import re
import sys
import time
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
UA = {"User-Agent": "data-webpage-pipeline (https://github.com/ricskoch/data-webpage)"}
GMT_URL = "https://reactome.org/download/current/ReactomePathways.gmt.zip"
VERSION_URL = "https://reactome.org/ContentService/data/database/version"
LICENCE_URL = "https://reactome.org/license"
PATHWAY_ID = re.compile(r"^R-HSA-\d+$")


def parse_gmt(text):
    """Parse GMT lines `name<TAB>pathway id<TAB>gene...`. Returns (pathways, rejects); never drops a line silently.

    pathways: list of {"id", "name", "genes"} with genes de-duplicated and sorted; rejects: list of (line number, reason).
    """
    pathways, rejects, seen = [], [], set()
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            rejects.append((n, "fewer than 3 tab-separated fields"))
        elif not PATHWAY_ID.match(parts[1].strip()):
            rejects.append((n, f"pathway id {parts[1]!r} is not R-HSA-<number> (not a human pathway)"))
        elif parts[1].strip() in seen:
            rejects.append((n, f"duplicate pathway id {parts[1].strip()}"))
        else:
            genes = sorted({g.strip() for g in parts[2:] if g.strip()})
            if not genes:
                rejects.append((n, "no gene symbols"))
                continue
            seen.add(parts[1].strip())
            pathways.append({"id": parts[1].strip(), "name": parts[0].strip(), "genes": genes})
    return pathways, rejects


def licence_evidence(html):
    """Sentences of the licence page that mention a Creative Commons licence, so a human can confirm the licence."""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    return [s.strip() for s in re.split(r"(?<=[.!?]) ", text) if re.search(r"creative commons|\bCC ?0\b|\bCC BY\b", s, re.I)][:8]


def get(url, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:  # network errors: retry with backoff, then fail loudly
            if attempt == tries - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 ** (attempt + 1))


def main(work):
    work = pathlib.Path(work)
    (work / "site").mkdir(parents=True, exist_ok=True)
    (work / "out").mkdir(parents=True, exist_ok=True)
    raw = get(GMT_URL)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = next(n for n in z.namelist() if n.endswith(".gmt"))
        text = z.read(name).decode("utf-8")
    pathways, rejects = parse_gmt(text)
    if len(pathways) < 1000:  # Reactome has about 2,800 human pathways; far fewer means the file changed shape
        raise SystemExit(f"only {len(pathways)} pathways parsed; refusing to write")
    try:
        release = get(VERSION_URL).decode().strip()
    except RuntimeError:
        release = "unknown"
    (work / "site" / "pathways.json").write_text(json.dumps({"release": release, "pathways": pathways}, separators=(",", ":")))
    with open(work / "out" / "rejects.csv", "w", newline="") as f:
        csv.writer(f).writerows([("line", "reason"), *rejects])
    try:
        evidence = licence_evidence(get(LICENCE_URL).decode("utf-8", "replace"))
    except RuntimeError as e:
        evidence = [f"licence page not readable: {e}"]
    genes = {g for p in pathways for g in p["genes"]}
    report = [f"# Reactome pathways build", "", f"- Release: {release}", f"- Pathways written: {len(pathways)}",
              f"- Distinct gene symbols: {len(genes)}", f"- Lines rejected (see rejects.csv): {len(rejects)}",
              f"- Source file: {GMT_URL} ({len(raw):,} bytes)", "", "## Licence evidence (confirm before publishing)", *[f"- {s}" for s in evidence]]
    (work / "out" / "report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(sys.argv[1])
