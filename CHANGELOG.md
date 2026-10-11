# Changelog

## Unreleased
- F20/F21: drug and other treatment names now reach the site. `export_site.py` joins the `conditions` table into `screens.json` (`treatment`, `treatment_dose`, `treatment_duration`); `/data` and `/gene` get a Treatment column, a Treatment filter and treatment search; `/data` also gets a Setup filter (drug, virus, timecourse...). Needs one re-run of "Publish data to R2 staging".
- M3b step 1: cell line context pipeline (`datasets/cell-line-context/`): matches every ORCS screen's cell line to Cellosaurus (and through it to DepMap), never guessing ambiguous names; GitHub job downloads the sources, records licence evidence and reports coverage. Publishes nothing.
- M3 quick win (F4, F20, F21): the screens table on `/data` and the results table on `/gene` get filters (cell line, study, library, phenotype, selection, comparability, hit), a text search, column sorting and 25/50/100-row pages (`src/scripts/table.ts`). New plain-language key to the scores (`ScoreExplainer`) on both pages.
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
