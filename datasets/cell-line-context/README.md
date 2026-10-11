# Cell line context (M3b)

Adds who each screened cell line is (Cellosaurus) and, in later steps, its mutations, expression,
copy number and ploidy (DepMap). Plan: `/mnt/project-files/plans/m3-biological-context.md` (project files).

Step 1, this folder: `fetch_map.py` downloads Cellosaurus and the DepMap file listing, matches every ORCS
screen's cell line name, and writes a coverage report. Names that fit two cell lines are never guessed;
they are listed in `unmapped_labels.csv` and fixed by hand in `dataset.yaml` (`overrides`).

Run on GitHub: workflow "Cell line context: sources and matching" (runs on PRs touching this folder).
Tests: `python3 -m unittest discover -s datasets/cell-line-context/tests`.

Step 2: `build.py` downloads the DepMap release files (via its figshare mirror), keeps only the 635 or so lines
ORCS screened, and writes Parquet tables (`cell_lines`, `screen_cell_lines`, `mutations`, `expression`,
`copy_number`) plus small JSON files for the website: `site/ctx/lines.json` (one context card per line) and
`site/ctx/g/NNNN.json` (per gene: expression, copy number and mutations, in the same gene shards as the ORCS
lookup). Only protein-altering mutations are kept (VEP impact HIGH or MODERATE, not synonymous); every filter is
counted in `build_report.md`. Upload to staging: manual workflow "Publish cell line context to R2 staging".

Sources and licences: Cellosaurus (CC BY 4.0, SIB) and DepMap Public 24Q4 (CC BY 4.0, Broad Institute,
figshare record). Both require attribution on the site.
