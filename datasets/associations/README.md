# Precomputed associations (redesign step 3)

For every gene: does its dependency differ between two groups of cell lines? The questions are each tissue against all
other tissues, and each driver-panel gene (the panel in `datasets/cell-line-context/dataset.yaml`) mutated against
wild-type. This is the biological-workflow comparison of `/gene` (`src/scripts/workflow.ts`), run for all genes at once.
Method approved by Richard on 2026-10-18; a short version of the text below is shown on the page.

## Method
1. One value per gene and cell line: the median of the line's screens on the essential-gene scale (0 = like a
   non-essential gene, -1 = like a core-essential gene). A line screened ten times counts once.
2. Effect: median of group A minus median of group B. Negative means the gene matters more in group A.
3. Two-sided Mann-Whitney U test (normal approximation, tie and continuity correction). At least 5 lines per group.
4. Benjamini-Hochberg false discovery rate (q) across all genes tested for one question. The questions are not
   corrected against each other, so a result is a lead to follow up, not a finding.
5. Lines flagged as misidentified or contaminated are left out; for mutation questions so are lines without mutation calls.

No bootstrap interval here (it would be 4000 resamples for every one of about a million tests); the `/gene` page gives the
interval for any single question.

## Run and test
`python3 -m unittest discover -s datasets/associations/tests` (unit tests, synthetic data). The statistics are compared with
SciPy in `tests/reference/test_associations_reference.py`. Workflow "Associations" builds from the published staging data and
fails unless four textbook cases come out right (KRAS, BRAF, PIK3CA dependency in mutant lines; MDM2 not needed in TP53-mutant
lines). Output: `site/assoc/index.json` (questions, gene list) and `site/assoc/f/NNN.json` (per question: gene index, effect,
p, q, lines per group).
