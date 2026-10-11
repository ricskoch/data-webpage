# Cell line context (M3b)

Adds who each screened cell line is (Cellosaurus) and, in later steps, its mutations, expression,
copy number and ploidy (DepMap). Plan: `/mnt/project-files/plans/m3-biological-context.md` (project files).

Step 1, this folder: `fetch_map.py` downloads Cellosaurus and the DepMap file listing, matches every ORCS
screen's cell line name, and writes a coverage report. Names that fit two cell lines are never guessed;
they are listed in `unmapped_labels.csv` and fixed by hand in `dataset.yaml` (`overrides`).

Run on GitHub: workflow "Cell line context: sources and matching" (runs on PRs touching this folder).
Tests: `python3 -m unittest discover -s datasets/cell-line-context/tests`.
