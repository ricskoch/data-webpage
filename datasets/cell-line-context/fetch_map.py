"""Step 1 of the cell line context data (M3b): download sources, match ORCS cell lines, report coverage.

Usage: python3 -I fetch_map.py <work_dir>
Writes <work_dir>/out/: screen_cell_lines.csv (one row per ORCS screen), unmapped_labels.csv (with reasons),
depmap_files.csv (what the DepMap release offers), report.md (also printed). Publishes nothing.
"""
import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import sys
import time
import urllib.request

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import context  # noqa: E402

CONFIG = yaml.safe_load((HERE / "dataset.yaml").read_text())
UA = {"User-Agent": "data-webpage-pipeline (https://github.com/ricskoch/data-webpage)"}


def get(url, dest=None, tries=4):
    """Download with retries; returns bytes, or writes to dest and returns its path."""
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                if dest is None:
                    data = r.read()
                    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
                with open(dest, "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
                return dest
        except Exception as e:  # network errors: retry with backoff, then give up loudly
            if attempt == tries - 1:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(2 ** (attempt + 1))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def licence_evidence(url, patterns):
    """Fetch a licence or terms page and return the sentences that mention a licence (evidence for the report)."""
    try:
        text = re.sub(r"<[^>]+>", " ", get(url).decode("utf-8", "replace"))
    except RuntimeError as e:
        return [f"could not fetch: {e}"]
    text = re.sub(r"\s+", " ", text)
    hits = []
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            hits.append(text[max(0, m.start() - 160): m.end() + 160].strip())
    return hits[:4] or ["no licence statement found on the page"]


def write_csv(path, rows, fields=None):
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(work):
    out = work / "out"
    out.mkdir(parents=True, exist_ok=True)
    src = CONFIG["sources"]
    report = ["# Cell line context: source check and matching report", ""]

    # 1. Cellosaurus
    cello = work / "cellosaurus.txt"
    get(src["cellosaurus"]["url"], cello)
    with open(cello, encoding="utf-8", errors="replace") as f:
        head = "".join(next(f) for _ in range(40))
    version = re.search(r"Version:\s*([\d.]+)", head)
    with open(cello, encoding="utf-8", errors="replace") as f:
        records = list(context.parse_cellosaurus(f))
    index = context.build_index(records, taxon=CONFIG["taxon"])
    report += ["## Cellosaurus", f"- Version {version.group(1) if version else 'unknown'}, "
               f"{cello.stat().st_size:,} bytes, SHA-256 `{sha256(cello)}`",
               f"- {len(records):,} records, {len(index['records']):,} human"]
    report += [f"- Licence evidence: {s}" for s in licence_evidence(src["cellosaurus"]["licence_page"],
                                                                     [r"CC BY[ -]?4\.0", r"Creative Commons"])]

    # 2. Match ORCS screens
    screens = json.loads(get(src["orcs_screens"]["url"]))
    rows, summary = context.map_screens(screens, index, CONFIG.get("overrides") or {})
    write_csv(out / "screen_cell_lines.csv", rows)
    labels = {}
    for r in rows:
        if r["cellosaurus_id"] is None:
            e = labels.setdefault(r["cell_line_label"], {"cell_line_label": r["cell_line_label"], "screens": 0,
                                                         "method": r["method"], "note": r["note"]})
            e["screens"] += 1
    unmapped = sorted(labels.values(), key=lambda e: -e["screens"])
    write_csv(out / "unmapped_labels.csv", unmapped, ["cell_line_label", "screens", "method", "note"])
    pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "n/a"
    report += ["", "## ORCS cell lines matched to Cellosaurus",
               f"- Screens: {summary['screens_mapped']:,} of {summary['screens']:,} "
               f"({pct(summary['screens_mapped'], summary['screens'])})",
               f"- Distinct cell line names: {summary['lines_mapped']:,} of {summary['lines']:,} "
               f"({pct(summary['lines_mapped'], summary['lines'])})",
               f"- Screens whose line has a DepMap ID: {summary['screens_with_depmap']:,} "
               f"({pct(summary['screens_with_depmap'], summary['screens'])}); distinct lines: "
               f"{summary['lines_with_depmap']:,}",
               f"- Screens on a line Cellosaurus flags as problematic (misidentified or contaminated): "
               f"{summary['screens_problematic']:,}",
               f"- By method: {summary['by_method']}", "", "Top unmatched names (screens, reason):"]
    report += [f"- {e['cell_line_label']!r}: {e['screens']} ({e['method']}{'; ' + e['note'] if e['note'] else ''})"
               for e in unmapped[:40]]

    # 3. DepMap: what the latest public release offers, and whether its model table agrees with Cellosaurus
    dm = src["depmap"]
    report += ["", "## DepMap"]
    try:
        text = get(dm["listing_url"]).decode("utf-8", "replace")
        report.append(f"- Listing starts with: `{text[:300]!r}`")
        listing = [{k.strip().lower(): (v or "").strip() for k, v in r.items() if isinstance(k, str)}
                   for r in csv.DictReader(io.StringIO(text))]
        report.append(f"- Listing columns: {list(listing[0]) if listing else 'empty'}; {len(listing):,} files")
        release, files, missing = context.pick_depmap_files(listing, dm["files"], dm["release_pattern"])
        write_csv(out / "depmap_files.csv", [r for r in listing if r.get("release") == release])
        report.append(f"- Latest public release: {release}; missing file types: {missing or 'none'}")
        report += [f"- {k}: `{v.get('filename')}` {v.get('size', '')}" for k, v in files.items()]
        if "models" in files:
            models = list(csv.DictReader(io.StringIO(get(files["models"]["url"]).decode("utf-8", "replace"))))
            cols = list(models[0]) if models else []
            report.append(f"- Model table: {len(models):,} models; columns include {cols[:25]}")
            rrid = next((c for c in cols if c.lower() == "rrid"), None)
            mid = next((c for c in cols if c.lower() in ("modelid", "depmap_id")), None)
            if rrid and mid:
                by_rrid = {m[rrid]: m[mid] for m in models if m.get(rrid)}
                ours = {r["cellosaurus_id"]: r["depmap_id"] for r in rows if r["cellosaurus_id"]}
                inmodel = [a for a in ours if a in by_rrid]
                agree = sum(by_rrid[a] == ours[a] for a in inmodel if ours[a])
                report.append(f"- Our matched lines found in the DepMap model table by RRID: {len(inmodel):,} of "
                              f"{len(ours):,}; DepMap ID agrees with Cellosaurus for {agree:,}")
    except Exception as e:  # report and carry on: the Cellosaurus part of the report is still useful
        report.append(f"- Could not read the DepMap listing: {type(e).__name__}: {e}")
    report += [f"- Licence evidence: {s}" for s in licence_evidence(dm["licence_page"],
                                                                     [r"CC BY[ -]?4\.0", r"Creative Commons"])]

    text = "\n".join(report) + "\n"
    (out / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]))
