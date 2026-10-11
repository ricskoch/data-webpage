# M2b, part 1: the conversion pipeline

**What it does:** takes the BioGRID download and turns it into the project's own tables, the "unified model". Think of it as transferring 1,952 tubes from 358 labs into one rack with one labelling scheme, while keeping each tube's original label taped on.

**The steps, in lab terms**
1. **Fetch** = receiving a reagent. Download the archive and compare its SHA-256 fingerprint with the one we recorded. A different fingerprint means a different lot: stop.
2. **Validate** = checking the delivery note. Every screen in the index must have a file, and the number of rows and hits in each file must match what the index says. One mismatch blocks the run.
3. **Convert** = relabelling. Each row gets our IDs, its native scores as numbers, and its line number in the source file (`source_row`), so any value can be traced back to the original line.
4. **Reject, never drop** = a deviation log. A row that cannot be read (a score that is not a number, a hit flag that is not YES or NO) goes to `rejected_rows.csv` with the reason. Kept rows + rejected rows must equal the source.
5. **Manifest** = the certificate of analysis: row counts, file sizes, checksums, licence, and the code version that made them.

**Three model choices in this step** (profile report section 10, items 3 to 5; easy to revert, each is one function):
- Duplicate genes inside a screen are kept as separate rows, distinguished by `source_row`.
- Hit-only screens are marked `result_scope = hits_only`, so later steps can leave them out of rank comparisons.
- Controls and IDs that are not Entrez genes keep their row, with `gene_id` empty and a reason (`control`, `unknown_identifier`, `ambiguous_identifier`).

**What you can check yourself:** open the latest "Ingest BioGRID ORCS" run on GitHub Actions and download the `biogrid-orcs-validation` artifact. `passed: true` and `rejected_rows: 0` are the two numbers that matter.

# M2b, part 2: comparable scores

**What it does:** adds three columns that put every screen on a common footing, beside the untouched native scores.
- `effect_rank` (A): where the gene sits in its screen, 0 = most depleted, 1 = most enriched. Like ranking samples on a plate instead of comparing raw fluorescence between plates.
- `effect_scaled` (B): a ruler with two marks, 0 = a typical non-essential gene, -1 = a typical core-essential gene. Like normalizing to a negative and a positive control. Only for negative-selection screens with at least 50 of each control gene set.
- `effect_z` (C): how unusual the gene is within its own screen, in robust standard deviations.

**Direction first:** a score is only usable once we know whether "low" means depleted. Order: a person's confirmation per study, the method's own convention (CERES, BAGEL), the control-gene test, else "unknown" and the three columns stay empty. P-values and FDRs never feed these columns: they say how sure, not which way.

**Blind control:** the control genes are split into two fixed halves. Half A sets the direction and the ruler; half B is held back to check the result, so the check is not graded on its own answer key.
