"""Draft drug identifier mapping (run on a GitHub runner; PubChem and ChEMBL are blocked from the cloud container).

Usage: python3 -I fetch_drugs.py <work_dir>   (reads <work_dir>/out/conditions.parquet, writes <work_dir>/drugs/)
Writes drugs.draft.yaml (for review, then commit as drugs.yaml) and drugs_report.md. Publishes nothing.
"""
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pandas as pd
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drug_names  # noqa: E402

GAP = 0.25  # seconds between any two calls (all threads together): 4 per second, under PubChem's limit of 5
WORKERS = 4
_gate = threading.Lock()
_next = [0.0]
errors = []


def _wait_turn():
    with _gate:
        now = time.monotonic()
        wait = _next[0] - now
        _next[0] = max(now, _next[0]) + GAP
    if wait > 0:
        time.sleep(wait)


def fetch_json(url, tries=3):
    """JSON from url; None when the service has no answer (4xx) or keeps failing (the error is recorded for the report)."""
    for k in range(tries):
        _wait_turn()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "data-webpage-drug-lookup (hobby project)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                return None
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            err = type(e).__name__
        time.sleep(2 ** k)
    errors.append(f"{err}: {url}")
    return None


def report(mapping, counts):
    lines = ["# Drug identifier draft", "", f"Labels: {len(mapping)}  " + ", ".join(f"{k} {v}" for k, v in counts.items()),
             f"Calls that failed after retries (treated as no answer): {len(errors)}", *[f"- {e}" for e in errors[:20]], "",
             "## Needs a person (unmapped or several PubChem matches)", ""]
    for label, e in mapping.items():
        for c in e["components"]:
            if c["status"] not in ("mapped", "not_a_compound"):
                lines.append(f"- `{label}` -> `{c['name']}`: {c['status']}, suggested CID {c['pubchem_cid']}")
    return "\n".join(lines) + "\n"


def main(work):
    out = pathlib.Path(work) / "drugs"
    out.mkdir(parents=True, exist_ok=True)
    cond = pd.read_parquet(pathlib.Path(work) / "out" / "conditions.parquet")
    labels = cond["agent_label"].dropna().unique().tolist()
    start = time.monotonic()

    def progress(done, total, name):
        if done % 20 == 0 or done == total:
            print(f"{done}/{total} drug names ({time.monotonic() - start:.0f}s), last: {name}", flush=True)
    mapping = drug_names.build_mapping(labels, fetch_json, workers=WORKERS, progress=progress)
    counts = drug_names.summary(mapping)
    (out / "drugs.draft.yaml").write_text(yaml.safe_dump(
        {"source": "PubChem PUG REST (public domain), ChEMBL API (CC BY-SA 3.0, IDs only)", "labels": mapping},
        sort_keys=True, allow_unicode=True))
    text = report(mapping, counts)
    (out / "drugs_report.md").write_text(text)
    print(text)
    print(json.dumps(counts))


if __name__ == "__main__":
    main(sys.argv[1])
