# Making CRISPR screen scores comparable: what the scores are and what we can do

Status: levels A, B and C approved by the owner 2026-10-11; bioinformatician review pending. Replaces proposals 1 and 2 in section 10 of `docs/data-profiles/biogrid-orcs-2.0.18.md`. Needs review by a bioinformatician before it goes into the data model.

**Honesty note.** The score descriptions below are from my knowledge of the published methods. I have not checked them against each study's notes in the BioGRID file; the profile only counted the score names. Where a definition varies by study, I say so. Whatever the pipeline does, it must keep each screen's native scores and record how they were defined.

## 1. The one idea behind every score

A CRISPR screen compares how many cells carry guides against a gene **before and after** something (time, a drug, a sorting step). A gene "scores" when its guides become rarer or more common. The scores differ in three ways: (a) **what they are contrasted to** (the reference), (b) **how many steps of processing** sit between raw guide counts and the number, (c) **whether they have a sign** (direction) or only say "how confident".

Lab analogy: the same plate read as raw fluorescence, as fold over blank, as a z-score within the plate, and as a p-value. Four numbers, one plate, four different questions.

## 2. The scores in BioGRID ORCS human 2.0.18

Counts are `SCORE.1` frequencies from the profile report. "Contrasted to" is the part you asked about.

| Score (SCORE.1 count) | How it is derived | Contrasted to | Unit and direction | Usable as effect size across screens? |
|---|---|---|---|---|
| **Bayes Factor** (375, BAGEL) | Guide-level fold changes are compared with two reference gene sets: known core-essential genes and known non-essential genes. The score says which set the gene's fold-change pattern resembles more. | The **reference sets**, not the control sample directly. | log2 Bayes factor. Positive = looks essential (profile: 0% of screens have essentials scoring lower, so positive means essential). | Monotone with depletion but not linear and not an effect size. Rank-comparable. |
| **CERES** (374, DepMap) | Log fold change versus the starting plasmid pool, with the **copy-number effect** (cutting many sites in amplified regions kills cells regardless of gene) modelled and removed. Then scaled per cell line. | Plasmid DNA for the fold change; scaled so that the **median non-essential gene = 0 and the median common-essential gene = -1**. | Dimensionless essentiality scale. Negative = depleted (profile: 99.7% consistent). | **Yes, already normalized.** This is the format we want everything in. |
| **Log2FC** (223) | log2(normalized guide counts at the end / counts at the start or in the control), averaged over a gene's guides (mean or median varies). | Start sample, plasmid, or control arm, depending on the study. | log2 units. Usually negative = depleted, but direction depends on the contrast (profile: only 58% of screens have essentials lower, so it is not reliable from the name alone). | Within a screen yes; across screens it depends on library, depth, duration and cell doubling time. Needs anchoring. |
| **MaGeCK Score** (199) | MAGeCK ranks guides by count change and aggregates ranks per gene (robust rank aggregation, RRA) or fits a model (MLE, giving a beta). The ORCS label does not say which. | The control sample, as defined by the study. | RRA score is a significance-like value (smaller = more significant); beta is a log-fold-change-like effect (signed). **Ambiguous.** | Not without reading the study. Profile: 62.5% direction consistency shows the mix. |
| **Z-score** (113) | The gene's average guide fold change expressed in standard deviations of the **same screen's gene population** (or of control guides). | The screen's own distribution. | SD units, usually negative = depleted (profile: 70%). | Within a screen only. A screen with many hits has a wider spread, which shrinks everyone's z. |
| **CRISPR Score** (89) | Varies by study. Often a log fold change normalized so that non-targeting or non-essential guides are zero and essential guides are about -1 (similar in spirit to CERES). | Non-targeting or reference genes, per study. | Signed. | **Possibly anchored already.** Must be checked per study. |
| **FDR** (72) and other p-values | A statistical test result, not an effect. | A null model. | Unsigned. | **No.** Says how sure, not how strong or which direction. |
| **STARS** (59) | Rank-based gene score (a hypergeometric-style test on guide ranks), computed separately for each tail. | The ranks within the screen. | Larger = stronger, but the sign comes from which tail was run. | Rank only. |

The remaining 46 or so score names are mostly variants of these families. Up to five scores per screen: the first is often the main effect, later ones are often p-values or FDRs.

**What the profile already showed:** 107 screens have an unsigned statistic as `SCORE.1`, 207 screens have only hits (no full gene list), and direction from the score name works for CERES and Bayes Factor only.

## 3. Can everything be transformed into one unified format?

**Not into one physical unit.** A Bayes factor, a p-value and a rank do not contain enough information to rebuild a log fold change. Converting them would produce numbers that look comparable and are not. The honest options are three levels, each weaker in what it claims and wider in coverage.

### Level A: rank percentile (works almost everywhere)
For every screen with a **signed** score and the **full gene list**: align the direction (negative = depleted), rank all genes within the screen, store `effect_rank` from 0 (most depleted) to 1 (most enriched). Needs no reference genes, no assumptions about score scale, and is exactly what the reproducibility analysis (Spearman) uses. It loses magnitude: "top 5%" in a screen with few real hits means less than in a screen with many.

### Level B: anchored effect scale (the CERES idea, applied to everything that qualifies)
Per screen, use the two reference gene sets (Hart CEGv2 core essentials and NEGv1 non-essentials, both in your profile): `effect_scaled = (score - median_NEG) / (median_NEG - median_CEG)`, with sign so that **0 = like a non-essential gene and -1 = like a typical core-essential gene**. This gives "depleted as strongly as a ribosomal gene" a single meaning across screens.
Requirements and limits:
- Negative-selection screens (essentiality-type phenotype), full gene list, score monotone in effect (Log2FC, CERES, Z-score, CRISPR Score, MAGeCK beta). Bayes Factor and rank-only scores: allowed only as "anchored, nonlinear", flagged.
- At least 50 reference genes of each set present (the profile found **1,402 of 1,952 screens, 72%**, meet this).
- Not valid for positive-selection, drug-modifier or sorting screens where essential genes are not the contrast. Those get Level A and Level C only.
- The reference sets define the scale, so they cannot also be the independent test in the known-biology check. Use disjoint halves, or other reference sets, for the check.

### Level C: robust z within screen (fallback for screens that cannot be anchored)
`effect_z = (score - median) / (1.4826 x MAD)` over all genes in the screen, after direction alignment. Says "how unusual is this gene in this screen". It is not comparable in magnitude across screens, but it is a bounded, documented, unit-free number and suits drug and positive-selection screens.

### Level D: recompute from raw guide counts (the real unification)
Only possible if a source provides guide-level counts. ORCS provides gene-level results only, so it is out of scope now and a reason to prefer sources with counts later.

## 4. Proposed storage (replaces section 10 proposals 1 and 2)

Per **screen** (`screens`, `score_defs`):
- `score_defs`: one row per native score column: position (1 to 5), native name, `method_family` (BAGEL, CERES, MAGeCK-RRA, MAGeCK-MLE, z-score, LFC, STARS, p-value, other, unknown), `reference_contrast` (plasmid, early timepoint, untreated control, reference sets, own distribution, unknown), `signed` (yes/no), `direction` (`lower_is_depleted` / `higher_is_depleted` / `unsigned` / `unknown`), `direction_evidence` (`documented` / `known_biology_test` / `human_confirmed` / `unresolved`).
- `screens.normalization_status`: `anchored` / `rank_only` / `robust_z` / `not_comparable`, plus `n_ceg_present`, `n_neg_present`.
- `screens.result_scope`: `all_genes` / `hits_only`.

Per **result row**:
- native scores `score_1..score_5` exactly as in the source (never overwritten).
- `effect_rank` (Level A), `effect_scaled` (Level B, null if not anchored), `effect_z` (Level C), `source_row`.

**What the UI shows and does:** cross-screen comparison uses `effect_rank` by default; uses `effect_scaled` only when both screens are anchored, with the label "scale anchored on core-essential genes"; shows the native score and its definition next to every value; never mixes native scores on one axis.

## 5. How direction gets decided
1. Documented: the method's own convention (CERES negative = depleted; BAGEL positive = essential).
2. Known-biology test: in negative-selection screens, compare the median of core-essential vs non-essential genes; if they separate clearly, direction is established, flagged `known_biology_test`.
3. Human confirmation per **study** (358 studies, not 1,952 screens), prioritising the large ones: Meyers 2017 and Behan 2019 cover 34% of screens.
4. Anything unresolved gets `unknown`, and its `effect_*` columns are null. Never guessed.

## 6. Cost and risks
- Compute: trivial (one pass per screen at ingestion).
- Review effort: the study-level direction table is the main human task; the pipeline proposes, a person confirms.
- Risk: Level B can look more authoritative than it is. Mitigation: the label, the `n_ceg/n_neg` counts, and the rule that quality flags travel with every comparison.
- Risk: MAGeCK RRA vs MLE ambiguity; mitigation: classify from the screen's notes and score names; unresolved stays `unknown`.

## 7. Decision needed
- **A (recommended):** Levels A, B and C as above. Broadest coverage, interpretable essentiality scale for 72% of screens.
- **B:** Level A only. Simplest and safest; loses magnitude, and the "how essential" language.
Either way, native scores are kept and a bioinformatician reviews the direction table and the scaling rule before M2b ships data.
