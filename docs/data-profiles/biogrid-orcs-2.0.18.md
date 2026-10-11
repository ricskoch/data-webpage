# Data profile: BioGRID ORCS 2.0.18, human (M2a)

Status: measured 2026-10-11. Roadmap item M2a ("profile report committed; licence text stored; mapping coverage reported").
Script: [`datasets/biogrid-orcs/profile.py`](../../datasets/biogrid-orcs/profile.py). Licence: [`datasets/biogrid-orcs/LICENCE-SOURCE.md`](../../datasets/biogrid-orcs/LICENCE-SOURCE.md).
No data from the file is in git. Numbers were cross-checked against a second, independent profile run in another session; every shared number matched.

**In one paragraph:** the file is clean as a container (every count in the index matches the files, no non-numeric scores, no missing gene IDs) but heterogeneous as science (52 score types, score direction not fixed by score name, 207 hit-only screens, duplicate genes inside screens). Think of it as 1,952 well-labelled tubes from 358 different labs, each measured with its own assay and units. The unified model in spec section 12 fits, with five changes proposed at the end.

## 1. Download and file

| Item | Value |
|---|---|
| Source URL that works | `https://downloads.thebiogrid.org/Download/BioGRID-ORCS/Release-Archive/BIOGRID-ORCS-2.0.18/BIOGRID-ORCS-ALL-homo_sapiens-2.0.18.screens.tar.gz` |
| Archive size | 752,653,348 bytes (753 MB) |
| SHA-256 | `39222a9650eed083edf193debe45eedc4aabc779ca04ea70107b6bd1efd9b8d7` |
| Uncompressed | 2,883,261,168 bytes (2.9 GB) |
| Contents | 1,952 per-screen files (`*.screen.tab.txt`) + 1 index file (`*SCREEN_INDEX*.index.tab.txt`). No licence or readme file. |

**Recipe for the M2b pipeline:** use `/Download/`, not `/File/` (the `/File/` URL returns a 13 KB HTML page). Use `curl --http1.1`: an HTTP/2 transfer was cut off at 253 MB, and the server does not support resuming. Verify the SHA-256 above before unpacking. The cloud environment needs `downloads.thebiogrid.org` on its allowed domains.

## 2. The two kinds of file

**Index file** (one row per screen, 38 columns): the "lab notebook" for each screen. Publication, cell line, library, enzyme, phenotype, treatment, score column names, hit rule.
**Screen files** (one row per gene per screen, 14 columns): the "plate reader output". `SCREEN_ID, IDENTIFIER_ID, IDENTIFIER_TYPE, OFFICIAL_SYMBOL, ALIASES, ORGANISM_ID, ORGANISM_OFFICIAL, SCORE.1 … SCORE.5, HIT, SOURCE`. Missing values are written as `-`.

## 3. Size and counts

| Measure | Value |
|---|---|
| Screens | 1,952 (index rows = files; none missing on either side) |
| Studies | 358 (1,940 screens from PubMed papers, 12 from preprints) |
| Result rows | 26,333,098 |
| Rows per screen | median 17,670; 5th percentile 179; max 36,106 |
| Hits (`HIT = YES`) | 1,777,315 rows (6.7%); median 761 per screen; 22 screens with zero hits |
| Hit-only screens (`FULL_SIZE_AVAILABLE = No`) | 207 screens, 321,278 rows: only the hits were published, not the full gene list |
| Index vs files | 0 mismatches in row count, hit count, and number of score columns |

**Study skew:** two studies make up 34% of screens: Meyers 2017 (340 screens, CERES) and Behan 2019 (325, BAGEL). Any "average across screens" is mostly these two labs.

## 4. Null rates

Screen files: identifiers, symbol, `SCORE.1` and `HIT` are 0% null. `SCORE.2` 32.9%, `SCORE.3` 72.5%, `SCORE.4` 86.4%, `SCORE.5` 95.4%, `ALIASES` 9.3%. Zero non-numeric values in any score column.
Index: `CONDITION_NAME` 57.1% and `CONDITION_DOSAGE` 64.3% (expected: untreated screens have none), `SIGNIFICANCE_CRITERIA` 14.3%, `MOI` 11.7%, `NOTES` 2.9%, `DURATION` 0.3%. All other columns, including cell line, library and phenotype, are 100% filled.

## 5. Score types per screen

- Screens report 1 to 5 score columns: 601 screens have 1, 733 have 2, 321 have 3, 215 have 4, 82 have 5.
- 52 distinct score names across all positions; 46 appear as `SCORE.1`. Most common `SCORE.1`: Bayes Factor 375, CERES 374, Log2FC 223, MaGeCK Score 199, Z-score 113, CRISPR Score 89, FDR 72, STARS 59.
- 107 screens have an unsigned statistic (FDR or p-value) as `SCORE.1`. These say "how sure", not "which direction", like a p-value without the fold change.

**Direction check (known biology).** For 1,402 full-size screens with at least 50 core-essential genes (Hart CEGv2) and 50 non-essential genes (Hart NEGv1), I compared the median `SCORE.1` of the two sets. In a negative-selection screen, essential genes should drop out.

| SCORE.1 type | Screens | Share where essentials score lower |
|---|---|---|
| CERES score | 374 | 99.7% (negative = essential, as expected) |
| Bayes Factor | 372 | 0% (positive = essential, as expected) |
| MaGeCK Score | 112 | 62.5% |
| Z-score | 84 | 70.2% |
| Log2FC | 71 | 57.7% |
| FDR | 69 | 30.4% |
| CRISPR Score (CS) | 38 | 97.4% |
| CasTLE Score | 30 | 16.7% |

Plain reading: for CERES and Bayes Factor the direction is fixed by the method. For MaGeCK, Z-score and Log2FC it is not: the same score name points different ways in different screens, partly because positive-selection and drug screens are mixed in. **Direction must be set per screen, not per score name.** This is the most important finding for the model.

## 6. Gene identifiers

- 99.0% of rows (26,074,421) use an Entrez Gene ID. 254,587 rows are `UNKNOWN` and 4,090 `AMBIGUOUS`.
- `UNKNOWN` is mostly controls and readthrough genes, not errors: `NTC` (non-targeting control) 13,062 rows, `0` 2,002, `ERCC6-PGBD3` 931.
- 27,815 distinct Entrez IDs. Against the current HGNC table (downloaded 2026-10-11): 2,574 are not in HGNC (often withdrawn or non-HGNC loci; not examined one by one), and 2,055 carry an older symbol than HGNC now uses. This is why the model joins on IDs, not symbols.
- 958 rows (27 symbols) are Excel-mangled dates, for example `1-Mar` for MARCHF1, `2-Sep` for SEPTIN2.

**Duplicate genes within a screen:** 60,162 (screen, gene) pairs appear more than once (150,271 rows, 1,463 screens). Only 2,445 pairs have identical scores, so these are not copy errors. Two patterns: 34 screens have more than 2% duplicates, mostly CRISPRa and CRISPRi libraries (21 of 34), where one gene is targeted at several promoters (inferred from the library type, not confirmed per screen). The other ~1,420 screens have a handful each, likely two source rows mapped to the same Entrez ID. The spec's assumption that (screen, gene) is a unique key is false.

## 7. Screen formats

| Field | Values (screens) |
|---|---|
| Library type | CRISPRn 1,823; CRISPRa 75; CRISPRi 48; base-editing knockout 6 |
| Screen type | Negative selection 1,002; positive and negative 424; positive 334; phenotype (e.g. FACS) 191; unknown 1 |
| Format | Pooled 1,934; in vivo 15; arrayed 3 |
| Setup | Timecourse 1,188; drug exposure 484; virus 155; toxin 20; cytokine 17; 88 more across 12 other values |

No combinatorial (gene pair) data: every result row is one gene. 8 screens use a genetic-interaction method (qGI) against a single engineered background, and 19 report a differential "CGI" score. These are single-gene rows with an interaction-type score, not pairs.

## 8. Metadata mapping coverage

Vocabulary download for cell lines (Cellosaurus) and NCBI Gene were blocked by the network policy, so coverage below is measured by rules, not by matching to the vocabulary. HGNC was reachable.

| Field | Filled | Distinct values | Mappable by rule | Notes |
|---|---|---|---|---|
| Cell line | 100% | 769 | 97.8% name a specific line | 43 screens are primary cells, organoids or iPSC-derived. No case or punctuation variants of the same name. Top 10 lines cover 25.7%. |
| Library | 100% | 139 | 79.0% standard named libraries | Rule is conservative: it counts "(Author, year)" libraries as custom. Top 10 libraries cover 71.4%. 139 values is a hand-curatable YAML file. |
| Phenotype | 100% | 27 | 100% | Already a short controlled list; a few near-duplicates ("viability", "cell viability"). |
| Treatment | 484 drug screens | 204 agents | 483 named, 466 with dose | 355 non-drug screens also name a condition (virus, toxin, cytokine). ChEMBL mapping not attempted. |

**All four fields mappable by rule: 1,521 screens (77.9%).** This is just below the 80% go/no-go threshold in spec section 11 for F22. Library is the limiting field. The "Similar" tier in section 13.1 allows libraries to differ, so the practical coverage for F22 is closer to the cell-line figure. A real Cellosaurus match is still needed before calling it.

## 9. Parquet size

All 26.3 M rows written as one table (screen ID, gene ID, ID type, symbol, 5 scores as numbers, hit as true/false), sorted by gene, zstd compression: **362 MB, 8x smaller than the text files**, well under the 1 GB split threshold in spec 6.2.
With 500,000-row groups (53 groups), one gene lookup would read one group, about 7 MB. That misses the 5 MB target in spec 6.4. Smaller row groups (around 100,000 rows) should fix it; M2b measures this.

## 10. What this means for the unified model (spec section 12)

These are proposals. Changing the unified model needs Richard's approval and a bioinformatician's review (AGENTS.md).

1. **Score direction per screen.** `effect` cannot be derived from `score_name` alone. Add `screens.effect_direction` (`lower_is_depleted` / `higher_is_depleted` / `unsigned`), set by the known-biology check and confirmed by a human for each study. Screens whose only score is FDR or p-value get `effect = null`.
2. **Keep all native scores.** Screens have up to 5 score columns. Store them in long form (one row per score) or as `score_1..5` with names in `screens`, instead of a single `effect_native`.
3. **Results key.** (screen, gene) is not unique. Add `source_row` (the line number in the source file) so every row stays traceable and nothing is collapsed. Decide in M2b whether duplicates are aggregated for cross-screen comparison, and how.
4. **Hit-only screens.** Add `screens.result_scope` (`all_genes` / `hits_only`). The 207 hit-only screens get no `rank_percentile` and are excluded from rank-based comparison (rule 12.3.4, "only compare what was tested").
5. **Controls are not genes.** Keep `NTC` and other `UNKNOWN` rows as rows with `gene_id = null` and a reason, so the known-biology check in 14.3 can use them as the zero line.

Confirmed as specified: one adapter per source; `screen_format = monogenic` for all 1,952 screens; drug screens fit `conditions` (agent, dose, duration all present). Treated and control arms are not linked in the source, so `parent_screen_id` has to be curated per study.

## 11. What I could not verify

- Vocabulary coverage for cell lines (Cellosaurus) and drugs (ChEMBL): hosts blocked. The 97.8% and 77.9% figures are rule-based.
- The full MIT licence text with BioGRID's copyright line: the `LICENSE.txt` host is blocked. Stored instead: the verbatim licence statement from the release page and the link (see `LICENCE-SOURCE.md`). Copy `LICENSE.txt` verbatim in M2b once the host is allowed.
- The cause of duplicate genes per screen is inferred from library type, not checked against the papers.
- The direction table uses the median of two gene sets; it does not prove each screen's direction. Hart's CEGv2 and NEGv1 lists (MIT licence, hart-lab/bagel) were used for this check only and are not stored here.
