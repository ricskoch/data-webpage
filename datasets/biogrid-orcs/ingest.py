"""BioGRID ORCS ingestion (M2b, spec 6.3 steps 1 to 4): fetch, validate, convert to Parquet, write manifest.

Usage:
  python3 -I ingest.py fetch   <work_dir>
  python3 -I ingest.py convert <work_dir> [--dry-run]

<work_dir>/raw holds the archive, <work_dir>/out the Parquet files, rejected rows, validation report and manifest.
--dry-run runs every check but writes no Parquet (for environments without pyarrow). Exit code 1 = a blocking
check failed. Nothing is uploaded anywhere: staging and promotion are separate, human-gated steps.
"""
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
import tarfile

import pandas as pd
from pandas.api.types import union_categoricals
import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter  # noqa: E402

CONFIG = yaml.safe_load((HERE / "dataset.yaml").read_text())
CATEGORICAL = ["screen_id", "perturbation_id", "gene_id_status", "symbol"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(work):
    """Download the pinned release. HTTP/1.1 because HTTP/2 transfers were cut off; no resume, so whole retries."""
    src = CONFIG["source"]
    raw = work / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / pathlib.Path(src["url"]).name
    for attempt in range(1, 5):
        r = subprocess.run(["curl", "--http1.1", "-sS", "-L", "--fail", "-o", str(target), src["url"]])
        if r.returncode == 0 and target.stat().st_size == src["bytes"]:
            break
        print(f"download attempt {attempt} failed or incomplete", file=sys.stderr)
    else:
        sys.exit("download failed 4 times")
    digest = sha256(target)
    if digest != src["sha256"]:
        sys.exit(f"checksum mismatch: got {digest}")
    (raw / "fetch.json").write_text(json.dumps({"url": src["url"], "bytes": target.stat().st_size, "sha256": digest,
                                                "retrieved_at": dt.datetime.now(dt.UTC).isoformat()}, indent=2))
    print(f"fetched {target.name}, checksum ok")


def extract(work):
    raw = work / "raw"
    dest = raw / "extracted"
    if not dest.exists():
        with tarfile.open(raw / pathlib.Path(CONFIG["source"]["url"]).name) as t:
            t.extractall(dest, filter="data")
    return dest


def load_index(src):
    files = sorted(src.rglob(CONFIG["source"]["index_glob"]))
    if len(files) != 1:
        sys.exit(f"expected one index file, found {len(files)}")
    index = adapter.read_tab(files[0])
    missing_cols = set(CONFIG["expected_columns"]["index_required"]) - set(index.columns)
    if missing_cols:
        raise adapter.SchemaError(f"index is missing columns {sorted(missing_cols)}")
    return index


def screen_files(src):
    out = {}
    for f in src.rglob(CONFIG["source"]["screen_glob"]):
        out[f.name.split("SCREEN_")[1].split("-")[0]] = f
    return out


def concat_categorical(parts):
    """pd.concat turns categoricals with different categories into text; union them to keep memory low."""
    parts = [p for p in parts if len(p)]
    out = {c: union_categoricals([p[c] for p in parts]) for c in CATEGORICAL}
    rest = pd.concat([p.drop(columns=CATEGORICAL) for p in parts], ignore_index=True)
    return rest.assign(**out)[parts[0].columns]


def convert(work, dry_run):
    src = extract(work)
    out = work / "out"
    out.mkdir(parents=True, exist_ok=True)
    index = load_index(src)
    files = screen_files(src)
    blocking = []
    ids = set(index["SCREEN_ID"])
    if ids != set(files):
        blocking.append({"check": "index_matches_files", "index_only": sorted(ids - set(files))[:20],
                         "files_only": sorted(set(files) - ids)[:20]})

    parts, rejected = [], []
    for sid in sorted(ids & set(files), key=int):
        with open(files[sid], newline="") as f:
            res, rej = adapter.parse_screen_file(f, sid, CONFIG)
        parts.append(res.astype({c: "category" for c in CATEGORICAL}))
        rejected.append(rej)
        if len(parts) % 200 == 0:
            print(f"parsed {len(parts)} screens", flush=True)
    results = concat_categorical(parts)
    rejected = pd.concat(rejected, ignore_index=True)

    screens = adapter.to_screens(index, CONFIG)
    tables = {"screens": screens, "studies": adapter.to_studies(index, CONFIG),
              "score_defs": adapter.to_score_defs(index), "conditions": adapter.to_conditions(index)}
    tables["perturbations"] = (results[["perturbation_id", "gene_id", "symbol"]].astype({"perturbation_id": str})
                               .drop_duplicates("perturbation_id").assign(kind="single").reset_index(drop=True))
    count_problems = adapter.check_screen_counts(screens, results, rejected)
    blocking += count_problems

    report = {
        "dataset": CONFIG["id"], "source_release": CONFIG["source"]["release"],
        "source_rows": int(len(results) + len(rejected)), "result_rows": int(len(results)),
        "rejected_rows": int(len(rejected)),
        "rejected_by_reason": rejected["reason"].value_counts().to_dict() if len(rejected) else {},
        "screens": int(len(screens)), "studies": int(len(tables["studies"])),
        "result_scope": screens["result_scope"].value_counts().to_dict(),
        "gene_id_status": results["gene_id_status"].value_counts().to_dict(),
        "duplicate_screen_perturbation_pairs": int(results.groupby(["screen_id", "perturbation_id"], observed=True)
                                                   .size().gt(1).sum()),
        "unmapped": {c: screens.loc[screens[c].eq("unmapped"), c].size
                     for c in ["perturbation_type", "selection_type", "result_scope"]},
        "blocking_problems": blocking,
        "passed": not blocking,
    }
    rejected.to_csv(out / "rejected_rows.csv", index=False)
    (out / "validation_report.json").write_text(json.dumps(report, indent=2, default=int))
    print(json.dumps({k: v for k, v in report.items() if k != "blocking_problems"}, indent=2, default=int))
    if dry_run:
        print("dry run: no Parquet written")
    else:
        write_parquet(out, results, tables)
        report["gene_slice"] = [gene_slice_bytes(out / "results.parquet", g) for g in CONFIG["parquet"]["probe_ids"]]
        print(json.dumps(report["gene_slice"], indent=2))
        (out / "validation_report.json").write_text(json.dumps(report, indent=2, default=int))
        write_manifest(work, out, report)
    if blocking:
        sys.exit(f"{len(blocking)} blocking problems, see validation_report.json")


def write_parquet(out, results, tables):
    """Sort by lookup key so Parquet min/max statistics let a reader skip row groups (spec 6.4)."""
    pq = CONFIG["parquet"]
    for c in pq["sort_by"]:
        results[c] = results[c].cat.set_categories(sorted(results[c].cat.categories), ordered=True)
    results.sort_values(pq["sort_by"]).to_parquet(out / "results.parquet", index=False, compression="zstd",
                                                   row_group_size=pq["row_group_size"])
    for name, t in tables.items():
        t.to_parquet(out / f"{name}.parquet", index=False, compression="zstd")


def gene_slice_bytes(path, perturbation_id):
    """Compressed bytes of the row groups a reader must fetch for one perturbation, from min/max statistics."""
    import pyarrow.parquet as papq
    meta = papq.ParquetFile(path).metadata
    col = meta.schema.names.index("perturbation_id")
    total = groups = 0
    for g in range(meta.num_row_groups):
        st = meta.row_group(g).column(col).statistics
        if st is None or not st.has_min_max or st.min <= perturbation_id <= st.max:
            total += meta.row_group(g).total_compressed_size
            groups += 1
    return {"perturbation_id": perturbation_id, "row_groups": groups, "of_row_groups": meta.num_row_groups,
            "compressed_bytes": total}


def write_manifest(work, out, report):
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(out.glob("*.parquet"))]
    manifest = {"id": CONFIG["id"], "collection": CONFIG["collection"], "version": "0.1.0-staging",
                "visibility": "not_published", "licence": CONFIG["licence"],
                "provenance": {"source": json.loads((work / "raw" / "fetch.json").read_text()),
                               "release": CONFIG["source"]["release"], "ingestion_commit": commit},
                "row_counts": {"results": report["result_rows"], "rejected": report["rejected_rows"],
                               "screens": report["screens"], "studies": report["studies"]},
                "validation_passed": report["passed"], "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("fetch", "convert"):
        sys.exit(__doc__)
    work_dir = pathlib.Path(sys.argv[2])
    if sys.argv[1] == "fetch":
        fetch(work_dir)
    else:
        convert(work_dir, "--dry-run" in sys.argv)
