# Reproducibility of repeated drug screens

When the same drug was screened in the same cell line more than once, how well do the screens agree? Method chosen by
Richard on 2026-10-18 (rank correlation plus overlap of the strongest genes).

## Method
1. Pairs: every two screens with the same drug and cell line, both with a published score vector (`s/NNNN.json`, the
   per-screen robust z that the `/drug` page uses) and the same native score name. A rank correlation depends on the sign
   of a score, and screens with different score types (for example DrugZ and a log fold change) can point opposite ways,
   so those pairs are not scored.
2. `rho`: Spearman rank correlation of the two screens' scores on the genes both report. 1 means the same order of genes,
   0 means unrelated, negative means opposite.
3. `overlap`: how many genes appear in both screens' list of 200 strongest genes (largest absolute z), counted among the
   shared genes, next to the number expected by chance (200 x 200 / shared genes; about 2 for 18,000 shared genes).
4. Pairs with fewer than 2,000 shared genes are not scored.
5. Every skipped pair is written to `out/skipped.csv` with its reason.

Pairs from the same study (other library) are marked: they share lab, protocol and often the cell stock, so they agree more
than screens from different labs.

## Run and test
`python3 -I reproducibility.py <work_dir>` reads the published staging files; unit tests in `tests/`; Spearman is checked
against SciPy in `tests/reference/test_reproducibility_reference.py` (runs in CI). Workflow: "Reproducibility" (manual
publish to R2 staging).
