# ADR 0003: Data pipeline layout and tooling

Status: proposed, 2026-10-11 (needs Richard's approval: adds pipeline dependencies)

**Decision**
- Each source gets an adapter in `datasets/<id>/`: `dataset.yaml` (source, checksum, mappings, rules), `adapter.py` (pure, tested transformation functions), `ingest.py` (fetch, validate, convert, manifest), `tests/`.
- Python 3.13 with three pinned packages: pandas (tables), pyarrow (Parquet), PyYAML (config). Tests use the standard library `unittest`, so no test framework is added.
- The pipeline runs on GitHub Actions runners (public repo, so free minutes). Nothing is uploaded to storage by the pipeline in this step.

**Why:** the profile in M2a already used pandas; Parquet needs pyarrow. These packages are used only by the pipeline and never reach the website.

**Trade-off:** pandas holds the whole 26 M row table in memory (about 2 GB). Fine on a 16 GB runner; a second, larger source may need chunked writing.

**Cost:** none. Runner minutes are free on a public repository.

**Change when:** a source no longer fits in runner memory, or a second source needs the same functions (then move shared code to `datasets/common/`).
