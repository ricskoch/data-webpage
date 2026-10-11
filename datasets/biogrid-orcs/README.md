# BioGRID ORCS adapter

Converts BioGRID ORCS (human) into the unified CRISPR model (spec section 12). Config: `dataset.yaml`. Licence: `LICENCE-SOURCE.md`.

```
pip install -r datasets/biogrid-orcs/requirements.txt
python -m unittest discover -s datasets/biogrid-orcs/tests
python -I datasets/biogrid-orcs/ingest.py fetch   /tmp/orcs    # downloads 753 MB, checks SHA-256
python -I datasets/biogrid-orcs/ingest.py convert /tmp/orcs    # writes /tmp/orcs/out
```

Outputs in `out/`: `results.parquet` (one row per source row, native scores, sorted by `perturbation_id`), `screens`, `studies`, `score_defs`, `conditions`, `perturbations` (Parquet), `rejected_rows.csv`, `validation_report.json`, `manifest.json`. A blocking check failure exits with code 1.

`normalize.py` adds the comparable score columns (`effect_rank`, `effect_scaled`, `effect_z`) and per-screen direction, using the primary score (first signed score column) and the Hart CEGv2/NEGv1 gene lists, which `fetch` downloads. The known-biology summary is in `validation_report.json`; it is flagged, not blocking, because the release gate is a human decision.

Not done here yet: vocabulary mapping, staging upload. `profile.py` is the M2a exploration script and is not part of the pipeline.
