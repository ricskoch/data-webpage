"""Draft drug identifier mapping (run on a GitHub runner; PubChem and ChEMBL are blocked from the cloud container).

Usage: python3 -I fetch_drugs.py <work_dir>   (reads <work_dir>/out/conditions.parquet, writes <work_dir>/drugs/)
Writes drugs.draft.yaml (for review, then commit as drugs.yaml) and drugs_report.md. Publishes nothing.
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import pandas as pd
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drug_names  # noqa: E402

DELAY = 0.25  # seconds between calls: well under PubChem's 5 requests per second


def fetch_json(url, tries=3):
    """JSON from url; None when the service says not found (404). Other errors are retried, then raised."""
    for k in range(tries):
        try:
            time.sleep(DELAY)
            req = urllib.request.Request(url, headers={"User-Agent": "data-webpage-drug-lookup (hobby project)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise
        time.sleep(2 ** k)


def report(mapping, counts):
    lines = ["# Drug identifier draft", "", f"Labels: {len(mapping)}  " + ", ".join(f"{k} {v}" for k, v in counts.items()), "",
             "## Needs a person (unmapped or several PubChem matches)", ""]
    for label, e in mapping.items():
        for c in e["components"]:
            if c["status"] != "mapped":
                lines.append(f"- `{label}` -> `{c['name']}`: {c['status']}, suggested CID {c['pubchem_cid']}")
    return "\n".join(lines) + "\n"


def main(work):
    out = pathlib.Path(work) / "drugs"
    out.mkdir(parents=True, exist_ok=True)
    cond = pd.read_parquet(pathlib.Path(work) / "out" / "conditions.parquet")
    labels = cond["agent_label"].dropna().unique().tolist()
    mapping = drug_names.build_mapping(labels, fetch_json)
    counts = drug_names.summary(mapping)
    (out / "drugs.draft.yaml").write_text(yaml.safe_dump(
        {"source": "PubChem PUG REST (public domain), ChEMBL API (CC BY-SA 3.0, IDs only)", "labels": mapping},
        sort_keys=True, allow_unicode=True))
    (out / "drugs_report.md").write_text(report(mapping, counts))
    print(json.dumps(counts))


if __name__ == "__main__":
    main(sys.argv[1])
