# M2a: Profile the first dataset

**What we did:** downloaded BioGRID ORCS 2.0.18 (human), measured what is actually inside, and wrote it up in [the profile report](../data-profiles/biogrid-orcs-2.0.18.md). No data is stored in git.

**Why before any pipeline code:** you characterise a new reagent before you build an assay on it. The spec's data model was written from memory of the format; the profile tests those assumptions against the real file. Five of them needed changing (report section 10).

**New concepts:** data profile, null rate, checksum verification, score direction, known-biology check, Parquet row group.

**What you can check yourself**
1. Open the report and read the one-paragraph summary and section 10. Those are the decisions you will be asked to make.
2. Section 5's direction table is the "positive control": essential genes must score as depleted. Where the share is near 100% or 0%, the method's direction is consistent; in between, it is not.
3. Section 8 compares mapping coverage with the 80% go/no-go threshold from spec section 11.

**How it can go wrong:** the metadata coverage numbers are rule-based, because the cell-line vocabulary could not be downloaded. They may be optimistic or pessimistic until checked against Cellosaurus in M2b.
