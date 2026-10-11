# Changelog

## Unreleased
- Prototype: Data overview (`/data`) and Gene lookup (`/gene`) pages reading JSON from the R2 staging bucket; `export_site.py`; manual "Publish data to R2 staging" workflow; runbook `docs/ops/r2-staging.md`.
- M2b part 2: comparable score columns (levels A, B, C), score family table in `dataset.yaml`, direction rules, known-biology summary.
- Reverted the TypeScript 7 bump (#5): `@astrojs/check` requires TypeScript 5.
- Visual identity: Victorian botanical plate look (parchment, ink, watercolour molecular icons), design tokens in `src/styles/tokens.css`, style guide `docs/design/style-guide.md`.
- M2b part 1: BioGRID ORCS adapter (fetch, validate, convert to Parquet, manifest), unit tests, ingestion workflow on GitHub Actions; ADR 0003.
- Spec v0.3: score normalization design (rank, anchored and robust-z effect columns beside native scores); proposal doc `docs/score-normalization.md`.
- Cloudflare deploy: `wrangler.jsonc`, `.node-version`, corrected deploy instructions.
- M2a: BioGRID ORCS 2.0.18 human profile report, profiling script, licence statement, and proposed changes to the unified model.
- M1: Astro + TypeScript site with Home, About, Data policy and 404 pages; CI for typecheck, build, audit and browser tests.
- M0: repository rules, PR template, CI secret scan, runbooks.
