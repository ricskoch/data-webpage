# Scientific Data Explorer: Scope and Architecture Spec (v0.3)

Owner: Richard. Status: draft for approval. No implementation until sections 3 and 10 are signed off.
Date: 2026-10-11. v0.2 revises v0.1 after your review comments. v0.3 adds the score normalization design (sections 12.2, 12.3, 12.8; details in `docs/score-normalization.md`), approved by the owner on 2026-10-11 and still awaiting bioinformatician review.

**What changed in v0.2** (new material is in sections 12 to 17; the earlier sections are patched where noted):
1. The product is now defined by one unified CRISPR data model (monogenic, combinatorial, drug + CRISPR) that makes screens from any source browsable and comparable, with experiment metadata attached (section 12). This replaces the "one dataset = one page" view as the core idea.
2. Reproducibility analysis between screens with identical or similar background is a feature (F22, F23; section 13).
3. Bioinformatics specialist work is planned explicitly, not only data collection (section 14).
4. Commercialization: what to change and what not to change yet (section 15).
5. Cost and effort guardrails so you do not have to review everything (section 16).
6. First-timer learning path (section 17).
7. Scope is human data only. BioGRID ORCS release 2.0.18, MIT licence (your confirmation).
8. Future multi-data-type and cross-dataset agent layer is out of scope, but the design leaves hooks for it (section 12.7).

**Not done in this revision:** I could not download the BioGRID file. This sandbox's network policy blocks `downloads.thebiogrid.org`, so I have not profiled the real file. Everything I say about its columns and size is from general knowledge of the format and is marked "verify". Profiling it is the first task of M2.

## 0. Decisions already made (inputs)

| # | Decision | Value |
|---|---|---|
| D1 | Primary audience | Curious non-specialists and wet-lab scientists without bioinformatics training. Education first, exploration second. |
| D2 | Launch source | BioGRID ORCS, human only, release 2.0.18 (`BIOGRID-ORCS-ALL-homo_sapiens-2.0.18.screens.tar.gz`), MIT licence. Main aim: every current and future CRISPR dataset (monogenic, combinatorial, drug + CRISPR) in one standard format, browsable and comparable with experiment metadata. |
| D3 | Size ceiling for MVP | About 1 GB per dataset, analysis in the browser. |
| D4 | Restricted data | Possible later. Design for it now, build it later. The site should promote standardized data usage. |
| D5 | Publisher | Only Richard, for now. |
| D6 | Language | English only. |

Assumptions I added (all listed again in section 11): the site is free to use and has no accounts; the content is public and openly licensed in the MVP; BioGRID ORCS file sizes and column layout are verified at the start of M2, not assumed.

---

## 1. Product vision and problem statement

**Problem.** Large public datasets such as CRISPR screens exist as multi-hundred-MB tab-delimited dumps. A wet-lab biologist who wants to ask "is my gene essential in my cell line?" must download, parse and join files in R or Python. Most do not, so they rely on a few hard-coded gene-level web lookups that cannot be combined or reproduced.

**Vision.** A website where a non-programmer can open a standardized dataset, ask a concrete question through a guided analysis, see an interactive result, and get the exact configuration and filtered data to reproduce it. Every dataset is presented in the same standardized form (same metadata, same provenance, same licence block, same download formats), which is the site's differentiator and the way it steers people toward standardized data use.

**Why people return.**
1. Each dataset ships with guided questions ("analysis recipes") that answer real lab questions in under 60 seconds.
2. Datasets are versioned and the site says what changed between versions.
3. Articles explain how to read the data and what the pitfalls are (for CRISPR: screen type, library, scoring method, cell-line context).
4. Shareable URLs: every result is a link that reproduces the same view.

**Out of scope for the initial release** (see section 3 for the full list): accounts, user submissions, server-side compute, private data, multi-language, comments, a general-purpose data-science notebook.

---

## 2. Audience and user journeys

### Personas
| Persona | Need | Success |
|---|---|---|
| P1: Bench scientist (primary) | Check a gene or gene list against public screens before an experiment | Answer in under 2 minutes with no installs |
| P2: Student / curious reader | Understand what a CRISPR screen is and see real data | Reads an article, plays with an embedded chart |
| P3: Computational colleague (secondary) | Cite, download and reuse the data in a standard format | Gets Parquet/CSV, a checksum and a citation string |

### Primary journeys
- **J1 Gene lookup (MVP core).** Home -> dataset page -> "Look up a gene" recipe -> enter gene symbol -> see hit calls and scores across screens, filtered by cell line / screen type -> copy link or download filtered CSV.
- **J2 Compare a gene list.** Paste up to 100 genes -> table + heatmap of scores across selected screens -> download.
- **J3 Learn.** Article ("How to read a CRISPR screen") with embedded live chart from the dataset -> link to the dataset page.
- **J4 Cite and reuse.** Dataset page -> copy citation, licence, version, checksum -> download Parquet/CSV.
- **J5 Browse.** Catalogue -> filter by domain, type, licence -> open dataset.

---

## 3. MVP feature list, priorities, and explicit exclusions

Priority: **E** = essential for MVP, **R1** = first subsequent release, **D** = deferred until there is demonstrated demand.

| ID | Feature | Pri | Rationale | Testable acceptance criterion |
|---|---|---|---|---|
| F1 | Homepage (purpose, featured dataset, latest articles) | E | Credibility and orientation | Loads with no JS errors; states purpose in under 60 words above the fold; links to the catalogue and the BioGRID ORCS dataset page |
| F2 | Dataset catalogue (list + filter by tag/domain/licence + text search over title/description) | E | Establishes the multi-dataset structure even with 1 dataset | Catalogue lists all published datasets; filters change results correctly in a Playwright test; works with 1 and with 50 mock datasets |
| F3 | Dataset detail page (description, provenance, references, licence, version, citation, schema, checksums, changelog) | E | Core of scientific credibility and standardization | Every mandatory field in section 5 renders; build fails if a published dataset lacks any mandatory field |
| F4 | Interactive table with column filters and sorting (server-less) | E | Basic exploration | On BioGRID ORCS, a filter on gene symbol returns first rows in under 2 s on a warm cache and transfers under 50 MB |
| F5 | Guided analysis recipes (2 for MVP: gene lookup, gene-list comparison) | E | Makes data usable by non-bioinformaticians; the main value | Each recipe runs from the UI with no code, returns correct results versus a Python reference calculation on 10 test genes |
| F6 | Charts (Plotly): score distribution, per-screen dot plot, heatmap | E | Visual exploration | Charts render on desktop and 375 px width; hover shows the value; keyboard-focusable controls |
| F7 | Download: filtered CSV, full Parquet, `datapackage` metadata, SHA-256 | E | Reuse and trust | Downloaded file's SHA-256 matches the manifest; filtered CSV row count equals on-screen count |
| F8 | Reproducible analysis configuration (recipe parameters in URL + downloadable JSON) | E | Reproducibility is the scientific selling point | Opening a saved URL or importing the JSON gives byte-identical result tables |
| F9 | Articles and methodology pages (CMS-driven) | E | Education, returning visitors, SEO | Richard publishes an article from Sanity and it is live within 5 minutes with no code change |
| F10 | Related content links (dataset <-> article, by explicit CMS references) | R1 for automatic; E for manual references | Navigation | Dataset page lists linked articles; article lists linked datasets |
| F11 | Responsive layout, WCAG 2.2 AA basics | E | Reach and credibility | Lighthouse accessibility >= 95; axe-core has 0 critical issues on the 5 key templates; usable at 375 px |
| F12 | About, methodology, data policy, licence pages | E | Trust, legal basis | Pages exist and are linked from the footer |
| F13 | Cookieless analytics | E | Know if anyone uses it, no consent banner | No cookies set (verified in Playwright); page-view counts visible in dashboard |
| F14 | Full-text site search (Pagefind) | R1 | Few pages at launch; browsing is enough | n/a for MVP |
| F15 | Second and third datasets, dataset versioning UI (diff between versions) | R1 | Proves the standardized pipeline generalizes | A new dataset is added using only a manifest + ingestion config, no new page code |
| F16 | Access-controlled (private) datasets | D (design now, build later) | Needed per D4, not for launch | Section 8 gate exists in CI and rejects a public publish of a private dataset |
| F17 | Server-side compute for >1 GB data | D | Not needed at 1 GB | Trigger in section 9 |
| F18 | Accounts, bookmarks, saved analyses | D | Share-by-URL covers 90% of need with no personal data | Revisit if >=20 requests |
| F20 | Unified screen browser: browse all screens across sources, filter by cell line, library, perturbation type, screen format (monogenic / combinatorial / drug + CRISPR), phenotype, treatment | E | This is the core of your stated aim | Filters operate on the unified `screens` table; each result row links to its source screen and publication |
| F21 | Cross-screen gene view: one gene across all selected screens with experiment context shown next to each score | E | The "joint insight with context" use case | Gene lookup returns one row per screen with cell line, library, method and standardized effect; matches Python reference on 10 genes |
| F22 | Reproducibility analysis, pairwise: pick two screens (or a suggested matching pair), see correlation, hit overlap, scatter, shared-gene count, caveats | E (core, but the narrowest version) | Your requested feature; pairwise is testable and has well-known statistics | Spearman r, Jaccard and hypergeometric p match `scipy` to 1e-6 on 5 reference pairs; pair with under 2,000 shared genes shows a warning |
| F23 | Reproducibility, grouped: auto-group screens with identical or similar background, show a reproducibility summary per group | R1 | Depends on metadata quality being proven first | Groups are generated from documented matching rules; each group shows the rule that formed it |
| F19 | User submissions | D | Moderation burden, licence risk | Revisit only after 3+ external requests |

**Explicit exclusions from the MVP:** accounts, user submissions, comments, newsletters, server-side queries, custom SQL editor for general visitors (an advanced SQL panel is R1), notebooks, multi-language, payments, API for third parties.

---

## 4. Page hierarchy and navigation

```
/                          Home
/datasets/                 Catalogue (search + filters)
/datasets/{slug}/          Dataset detail (overview, schema, provenance, versions, downloads)
/datasets/{slug}/explore/  Exploration workspace (recipes + table + charts)
/screens/                  Unified screen browser across all sources (F20)
/screens/{id}/             One screen: experiment metadata, conditions, top results, source link
/compare/                  Reproducibility workspace (F22/F23), URL holds the selected screens
/datasets/{slug}/explore/?recipe=gene-lookup&gene=BRCA1&...   (shareable state)
/learn/                    Articles index
/learn/{slug}/             Article (can embed live charts)
/about/                    About
/methodology/              How data is curated, standardized, versioned
/data-policy/              Licences, attribution, takedown, privacy
/changelog/                Site and dataset release notes
/404
```

Primary nav: Datasets, Learn, Methodology, About. Footer: Data policy, Changelog, GitHub, licence.

### Page requirements (short)
- **Homepage:** purpose statement, one featured dataset card, 3 latest articles, one-click "Try: look up a gene" demo.
- **Catalogue:** card or table list, filters (domain, data type, licence, size), text search; each card shows version, last updated, licence badge, row count.
- **Dataset page:** tabs or anchored sections: Overview, Schema, Provenance and citation, Versions, Download, "Explore" call to action. Citation string and licence are visible without scrolling on mobile.
- **Workspace:** left panel recipe picker and parameters, main panel results (chart + table), top bar with "Copy link", "Download CSV", "Download config JSON". Shows the data volume loaded so far. Built for the two recipes, not as a generic dashboard.
- **Article pages:** reading width, table of contents, embedded chart blocks, linked datasets, references list, last-updated date.
- **About / methodology / data policy:** plain content pages from the CMS.

---

## 5. Content model (Sanity)

Principle: the CMS holds **editorial content and dataset descriptions**. It never holds the scientific data files. Technical facts (schema, row counts, checksums, file locations, version) come from the ingestion pipeline's manifest, not from manual entry, so they cannot drift.

### Schemas
**dataset** (editorial description of a dataset; one document per dataset, not per version)
- Mandatory: `title`, `slug`, `shortDescription` (<=200 chars), `description` (rich text), `domain` (ref), `datasetId` (must match the manifest id), `sourceName`, `sourceUrl`, `licence` (ref), `attributionText`, `citation` (text), `references` (>=1), `visibility` (`public` | `restricted`), `status`.
- Optional: `tags`, `relatedArticles`, `limitations`, `howToCite`, `featuredRecipes`.
- Not editable here: version, row counts, schema, checksums, file URLs (read from the manifest at build time).

**article**
- Mandatory: `title`, `slug`, `summary`, `body` (portable text), `author` (ref), `publishedAt`, `updatedAt`, `tags`, `status`.
- Optional: `relatedDatasets`, `references`, `embeddedViz` blocks (dataset + recipe + parameters), `coverImage` with alt text (alt text mandatory if an image is set).

**reference** (`title`, `authors`, `year`, `doi` or `url`), **licence** (`name`, `spdxId`, `url`, `requiresAttribution`, `allowsRedistribution`, `allowsCommercialUse`, `allowedForPublicRelease` boolean), **author** (`name`, `bio`, optional `orcid`), **domain/tag**, **page** (about, methodology, data policy).

### Editorial workflow
1. Draft in Sanity (status `draft`). 2. Preview URL (Astro preview deployment reading drafts). 3. Set status `published`. 4. Sanity webhook triggers a Cloudflare Pages deploy hook. 5. Site rebuilds, typically live within 2 to 5 minutes. 6. Content history is kept by Sanity; unpublish reverses it with the same webhook path.

Validation in Sanity: required-field rules plus a build-time check in Astro (build fails if a published dataset has no matching manifest, or the licence is flagged `allowedForPublicRelease: false`).

### CMS vs data-ingestion boundary
| Activity | Tool |
|---|---|
| Write or edit an article, fix a typo, add a reference, change tags, link datasets/articles | Sanity (no code) |
| Edit a dataset description, citation, limitations, featured recipes | Sanity (no code) |
| Add a new dataset or a new data version | Ingestion workflow (section 6), triggered via GitHub Actions |
| Change a dataset's schema, column semantics or recipe logic | Code change via pull request |

---

## 6. Data architecture

### 6.1 Components and justification
| Component | Choice | Reason | Trade-off | Cost | Change when |
|---|---|---|---|---|---|
| Site framework | Astro + TypeScript, static output | Content-heavy site, fast pages, ships JS only on interactive islands | Build-time content means a rebuild per publish | €0 | Need per-user dynamic pages -> add SSR on Cloudflare Workers |
| Hosting/CDN | Cloudflare Pages | Free static hosting, preview deploys per PR, global CDN | Vendor lock-in is low for static output | €0 within free limits | Build minutes or request limits exceeded (unlikely at hobby scale) |
| Object storage | Cloudflare R2 | Zero egress fees, S3-compatible, same network as Pages, supports HTTP range requests that DuckDB-Wasm needs | Needs a custom domain and CORS config for public reads | 10 GB free; about €0.014/GB-month above that | Need >500 GB or fine-grained per-user access control |
| Data format | Parquet (zstd, sorted and row-grouped by the main lookup key, e.g. gene) | Columnar, compressed (typically 5 to 20x smaller than TSV), lets the browser read only needed columns and row groups | Not human-readable; requires a conversion step | Lowers storage and transfer | Data is not tabular (images, arrays) -> Zarr/other |
| In-browser query | DuckDB-Wasm, lazy-loaded only on workspace pages | SQL over remote Parquet with range requests; no server to run or pay for | About 6 to 8 MB Wasm download on first workspace visit; memory limited to the browser tab (practically about 2 GB); weak on low-end phones | €0 | Dataset >1 to 2 GB uncompressed per query or median query transfer >100 MB -> precomputed aggregates, then server-side |
| Visualization | Plotly.js partial bundle (basic + heatmap) | Interactive, accessible hover and export, broad chart types, you listed it | Full bundle is about 3.5 MB; partial is about 1 MB; less elegant than custom d3 | €0 | Bundle size hurts mobile performance -> Observable Plot or uPlot for simple charts |
| Metadata store | JSON manifest per dataset version in the repo and in R2 (no database) | Small, versioned in git, diffable, readable at build time | No ad-hoc cross-dataset queries | €0 | See 6.7 |
| CMS | Sanity (free tier) | Visual editing, structured content, webhooks | Free-tier limits change; content is outside git | €0 (check limits) | Contributors or API traffic exceed free tier |
| Version control / CI | GitHub + GitHub Actions | PRs, checks, environments with approvals | Actions minutes limited on private repos | €0 on a public repo | Ingestion jobs exceed free minutes -> self-hosted runner or Cloudflare cron |
| Search | Pagefind (R1) | Static index built at deploy, no service | Index covers site content only, not data rows | €0 | Need typo tolerance or faceting at scale -> Typesense/Algolia |

### 6.2 Expected dataset sizes and formats (to verify in the M2 spike)
- BioGRID ORCS: distributed as tab-delimited archives plus per-screen files; order of thousands of screens and tens of millions of rows in total. **I have not verified current counts or sizes**, so the first task of M2 is a measured profile: raw size, row count, columns, null rates, and compressed Parquet size.
- Target after conversion: a few hundred MB of Parquet or less. If the Parquet exceeds 1 GB, split into a `scores` fact table (screen_id, gene_id, score, hit_call, ...) and a small `screens` dimension table (screen metadata) so most queries touch only a slice.
- Format rule: tabular data with more than 100k rows -> Parquet; smaller lookup tables -> Parquet or JSON; always also offer CSV on request-by-filter (generated in the browser).

### 6.3 Ingestion, validation, versioning, publication
A dataset is one directory in the repo (`datasets/biogrid-orcs/`) holding `ingest.py`, `dataset.yaml` (source URL, licence id, expected columns and types, key columns, validation rules, recipe definitions), and tests. Raw and processed data are **not** committed to git.

Pipeline (GitHub Actions, manual dispatch):
1. **Fetch** the pinned source release; record URL, retrieval timestamp, and source checksum.
2. **Validate** against `dataset.yaml` (Frictionless Table Schema / pandera): column names and types, key uniqueness, value ranges, null thresholds, row-count delta vs the previous version (flag if it changes by more than 20%).
3. **Convert** to partitioned, sorted Parquet; compute SHA-256 per file.
4. **Write manifest** (`manifest.json`): dataset id, semantic version, source release, row counts, schema, column descriptions, licence id, file list with sizes and checksums, ingestion git commit, `visibility`.
5. **Upload to staging**: `r2://staging/{id}/{version}/`.
6. **Human gate**: a PR shows the manifest diff and validation report; Richard approves in a GitHub Environment named `data-release`.
7. **Promote** to `r2://public/{id}/{version}/` (immutable; never overwritten) and update `r2://public/{id}/latest.json`. A site rebuild picks up the new manifest.

Versioning: semantic (`major.minor.patch`), where major = schema change, minor = new rows/screens from a new source release, patch = corrections. Old versions stay available.

Standardization: manifests follow a Frictionless Data Package-compatible structure with an added `provenance` and `licence` block. Identifiers: HGNC/Entrez gene IDs alongside symbols so datasets can be joined later.

### 6.4 How users query without downloading everything
- Parquet row groups sorted by gene; DuckDB-Wasm reads the footer (kilobytes), prunes row groups using min/max statistics, and fetches only matching ranges.
- Target: a single-gene lookup transfers under 5 MB; a 100-gene list under 30 MB; any recipe under 50 MB.
- Small, hot lookup tables (screen metadata, gene index) are also published as plain JSON (under 1 MB) so the first paint needs no Wasm.
- The UI shows data transferred and a warning before any action that would exceed 100 MB.

### 6.5 Browser vs server computation
| Runs in the browser (MVP) | Needs server-side (deferred) |
|---|---|
| Filter, group, aggregate, join of screens x scores, rank, heatmap matrices | Anything touching more than about 1 to 2 GB per query |
| Gene list comparison up to 100s of genes | Heavy statistics (e.g. re-running MAGeCK on raw counts) |
| CSV export of filtered data | Cross-dataset joins over many large datasets |
| | Private-data queries with per-user authorization |

### 6.6 Datasets too large for the browser
Order of escalation, cheapest first: (1) better sorting and partitioning; (2) precomputed aggregate Parquet (per-gene summaries) published as a separate "summary" table; (3) tile or sample views with a clear label; (4) a single Cloudflare Worker running a parameterised query service against R2 (about €5/month); (5) managed engine (MotherDuck or a small VM with DuckDB), only if (4) is insufficient.

### 6.7 When PostgreSQL / Supabase becomes necessary
Not in the MVP. Introduce it only if one of these becomes true: accounts or saved analyses with persistent user data; user submissions with moderation workflow; a need for transactional writes; cross-dataset relational queries that DuckDB over Parquet cannot serve within the 50 MB transfer target; or an access-controlled API. Expected cost then: Supabase free tier, or about €25/month for Pro.

### 6.8 Metadata, schema, provenance, checksums
Maintained by the pipeline, stored in the manifest, never hand-edited. The build compares the CMS `datasetId` with manifests and fails on mismatch. The website verifies checksums of downloads in CI (nightly job fetches the public files and compares SHA-256 to the manifest).

### 6.9 Assumptions that must be resolved before finalizing
1. BioGRID ORCS licence and redistribution terms (expected permissive, must be verified in M2 before any file is public).
2. Real Parquet size and query transfer volumes for ORCS (spike in M2).
3. Whether R2 public bucket + custom domain + CORS supports DuckDB-Wasm range reads without a Worker in front (spike).
4. Target browsers and devices (assumption: last 2 versions of Chrome, Firefox, Safari; phones with >= 4 GB RAM).

---

## 7. Release and maintenance workflow

### 7.1 Software releases
1. Issue or spec item -> agent opens a feature branch -> small PR (target under 400 changed lines).
2. CI on every PR: typecheck, lint, unit tests, Playwright smoke tests, axe accessibility, build, Lighthouse CI budget (JS <= 200 KB on non-workspace pages), dependency audit, secret scan.
3. Cloudflare Pages preview deploy per PR; Richard reviews the preview.
4. Merge to `main` by Richard only (branch protection: required checks, 1 human approval, no force pushes).
5. Production deploy from `main`; tag release; changelog entry.
6. **Rollback:** Cloudflare Pages keeps previous deployments, so rollback is one click or `git revert`. Target: restore in under 5 minutes.

### 7.2 CMS content publication
Sanity publish -> webhook -> deploy hook -> rebuild (2 to 5 min). Drafts are previewable on a protected preview URL. Rollback: restore the previous document version in Sanity, which triggers a rebuild. Content backup: nightly `sanity dataset export` stored in R2 (private bucket) with 30-day retention.

### 7.3 Dataset ingestion and release
As in 6.3, with the `data-release` environment approval. Rollback: repoint `latest.json` to the previous version (seconds, no re-upload). Immutable versions mean nothing is lost on rollback.

### 7.4 Minimum operational requirements
| Area | Minimum |
|---|---|
| Testing | Unit tests for ingestion validators and recipe logic; golden-file tests comparing recipe output to a Python reference on 10 genes; Playwright for the 5 key user journeys |
| Previews | Every PR has a preview URL; data-release PRs show the validation report |
| Backups | Git (code and dataset configs); R2 public data is reproducible from source plus pipeline and is mirrored monthly to a second private R2 bucket or external storage; Sanity export nightly |
| Monitoring | Uptime check (free tier) on home and one data file; nightly checksum verification; Cloudflare analytics for errors; email alert on failure |
| Dependency updates | Renovate or Dependabot weekly grouped PRs; patch/minor auto-merge only if all checks pass; majors reviewed by Richard |
| Data integrity | Checksums in manifests, immutable versions, nightly verification, row-count delta alarms at ingestion |

---

## 8. Security, privacy, licensing checklist

**Secrets**
- [ ] No secrets in git; secret scanning and push protection enabled.
- [ ] R2 write tokens only in GitHub Environment secrets (`data-release`), scoped to specific buckets; separate read-only token for the site build.
- [ ] Sanity tokens: read-only for the build, separate write token not given to the agent.
- [ ] The coding agent has no production credentials. Production deploys and data promotion require a human approval.

**Public vs private data**
- [ ] Two buckets: `public` and `restricted`. The public bucket contains only versions passed through the release gate.
- [ ] Every manifest has `visibility`. CI rejects promotion to `public` unless visibility is `public` AND the licence has `allowedForPublicRelease: true` AND a human approved.
- [ ] A pre-publish scan checks for personal-data-like columns (names, emails, IDs) and fails on a match unless explicitly allow-listed.
- [ ] No restricted data is accepted until the restricted-access design (signed URLs via a Worker, access logs) is built and reviewed.

**Input validation and abuse**
- [ ] No server-side user input in the MVP; the main inputs are URL parameters, which are validated with a schema before use and never rendered as HTML.
- [ ] Gene-list input capped (100 genes), URL length capped.
- [ ] Cloudflare WAF basic rules and rate limiting on the data domain; R2 request budget alert.
- [ ] CSP header restricting scripts to self and the analytics host.

**Dependencies:** lockfile, Renovate/Dependabot, `npm audit` and `pip-audit` in CI, minimal dependency policy (justify each new runtime dependency in the PR).

**Licensing and attribution**
- [ ] Each dataset has an SPDX licence id, attribution text, source URL and retrieval date; the page shows them above the fold.
- [ ] Original licence text is included in every download bundle.
- [ ] The site's own content and code licences are stated (suggest CC BY 4.0 for articles, MIT for code).
- [ ] Takedown contact and process on the data policy page.

**GDPR/privacy:** no accounts, no forms, no cookies, cookieless analytics (Cloudflare Web Analytics or Plausible/Umami), so no consent banner. Author names and ORCIDs in articles are editorial content with consent of the author. If personal data collection is ever added (accounts, submissions, contact form), a privacy notice, lawful basis, retention and deletion process are required first.

**Backups and restore:** monthly restore drill (rebuild site from git + manifest + R2 mirror in a scratch Cloudflare project). Document the procedure in `docs/restore.md`.

---

## 9. Budget (monthly, EUR)

| Item | Assumption | Expected | Type | Cost-surprise risk |
|---|---|---|---|---|
| Domain | .org or .com, about €12 to 15 per year | €1.0 to 1.3 | Fixed | Low; renewal price differs from year-one price |
| Hosting (Cloudflare Pages) | Static, free plan | €0 | Free tier | Build-minute and request limits; low |
| R2 storage | 2 to 10 GB at launch, 10 GB free | €0 | Free tier, then about €0.014/GB-month | 100 GB would cost about €1.4 |
| R2 operations | Range reads dominate; 10M reads/month free | €0 | Free tier, then per-million-request charge | Heavy Wasm usage by bots or many small range requests; set alerts |
| Egress | R2 has no egress fee | €0 | Free | Only if you add a paid proxy |
| CMS (Sanity free) | 1 editor, low API traffic since content is fetched at build | €0 | Free tier | Plan limits change; paid tier is roughly €15 per seat per month if contributors are added |
| Database | None in MVP | €0 | n/a | Supabase Pro about €25 if introduced |
| Analytics | Cloudflare Web Analytics | €0 | Free | n/a |
| Monitoring | Free uptime checks | €0 | Free | n/a |
| GitHub | Public repo, free Actions | €0 | Free | Private repo minutes limit |
| **Infrastructure total** | | **about €1 to 3** | | Well inside the €5 to 20 ceiling |
| AI coding subscription (separate budget) | Your existing Claude plan | €20 to 100+ | Fixed/usage-dependent | Not counted in the infrastructure ceiling; heavy agentic use can need a higher tier |

**Reserve for growth within the ceiling:** a Cloudflare Worker query service (about €5), a paid Sanity seat (about €15), or Supabase Pro (about €25, would exceed the ceiling alone).

**Reconsider the architecture when any of these happens:**
1. Median recipe transfers more than 100 MB, or p95 first result takes over 10 s on broadband.
2. Public data exceeds 100 GB or R2 operations exceed the free tier for 2 consecutive months.
3. Monthly infrastructure bill exceeds €15 for two months.
4. Any requirement for persistent user data.
5. A dataset above about 2 GB needs interactive querying.

Set Cloudflare billing alerts at €5 and €10.

---

## 10. Phased roadmap with milestones and acceptance criteria

| Phase | Scope | Exit criteria (all testable) |
|---|---|---|
| **M0 Foundations** (about 1 week) | Repo, CI skeleton, `AGENTS.md`/`CLAUDE.md` with working rules, branch protection, Cloudflare Pages preview, this spec in `docs/` | PR with a trivial change gets typecheck + test + preview; main is protected; secrets scan on |
| **M1 Walking skeleton** (1 to 2 weeks) | Astro site with Home, About, Data policy, one hard-coded sample dataset page, responsive layout, analytics | Deployed to production URL; Lighthouse perf >= 90, a11y >= 95 on Home; no cookies set |
| **M2a Profile and model** (1 to 2 weeks) | Download ORCS 2.0.18, profile it, write the unified model (section 12), draft vocabulary mappings, bioinformatics review of the model | Profile report committed; licence text stored; mapping coverage reported; model signed off by you and one bioinformatician |
| **M2b Pipeline** (2 to 3 weeks) | Ingestion + validation + standardization + Parquet + manifest, staging/promotion, R2 CORS + range reads check | Parquet row counts equal source; known-biology tests pass (14.3); browser test reads a gene slice transferring under 5 MB; promotion needs approval |
| **M3 Catalogue + dataset page** (1 to 2 weeks) | Catalogue, dataset detail from manifest, downloads with checksums, citation | F2, F3, F7 criteria pass; build fails on missing mandatory field |
| **M4 Workspace** (2 to 3 weeks) | DuckDB-Wasm, screen browser, interactive table, gene lookup, gene list, charts, shareable URL + config JSON | F4, F5, F6, F8, F20, F21 criteria pass; results match the Python reference on 10 genes; workspace works on a mid-range phone |
| **M4b Reproducibility** (2 weeks) | Pairwise comparison page (F22) with caveats and reference tests | F22 criteria pass; a bioinformatician has reviewed the statistics and caveat text |
| **M5 CMS and education** (1 to 2 weeks) | Sanity schemas, articles, methodology page, webhook publish, preview, 3 launch articles, related links | Publishing an article takes no code and is live within 5 min; content backup job runs |
| **M6 Hardening and launch** (1 week) | Backup/restore drill, monitoring, accessibility pass, CSP, performance budget, launch checklist | Restore drill completed in under 1 hour; all section 8 items checked; rollback tested |
| **Release 1.1** | Grouped reproducibility (F23), Pagefind search, a second source (ideally combinatorial or drug + CRISPR) added through config only, version comparison, automatic related content, advanced SQL panel | New source onboarded without new page code (F15) and without changing the unified model's tables |
| **Later (on demand)** | Server-side query Worker, restricted datasets, accounts, submissions | Only after the triggers in sections 6.6, 6.7 and 9 |

Rough total to launch: 13 to 18 weeks of part-time work with an agent (estimate; up from 9 to 13 in v0.1 because of the unified model and reproducibility; the M2a profile will tighten it).

### Agentic development workflow
**Agent responsibilities:** write code and tests for one roadmap item per PR; update docs and the changelog; run checks locally; open PRs with a description following the repo template; report what it could not verify; propose, never apply, dependency major upgrades and schema changes.
**Human-only decisions (Richard):** merging to `main`; approving `data-release`; any new dataset's licence acceptance; any change to secrets, permissions, DNS, billing or Cloudflare/GitHub settings; adding a new runtime dependency or paid service; schema-breaking changes; publishing restricted data.
**Working rules in the repo:** the spec is the source of truth (`docs/spec.md`); each PR references a feature ID (F1 to F19) and its acceptance criterion; the agent writes the failing test first for recipe logic; no PR above about 400 lines without a split; architecture decisions recorded as short ADRs in `docs/adr/`.

---

## 11. Unresolved questions and assumptions, ranked by impact

| Rank | Item | Impact | Default assumption | How to resolve |
|---|---|---|---|---|
| 1 | Metadata quality and mappability of BioGRID ORCS screens (cell line, library, phenotype, treatment) to controlled vocabularies | Decides whether comparison and reproducibility are meaningful at all | Most screens map; free-text remainder is flagged, not guessed | M2 profile: report % of screens with mapped cell line, library, phenotype. Go/no-go threshold: at least 80% mapped for F22 |
| 1b | BioGRID ORCS licence | Resolved by you: MIT. Still required: keep the copyright and licence notice with the data | MIT | Copy the licence text from the downloaded release into the repo at M2 |
| 2 | Recipe definitions and the comparability rules: which questions do your bench scientists need, and what counts as "similar background"? | Defines the workspace, F22 matching rules and the value of the product | Gene lookup, gene-list comparison, pairwise reproducibility; matching rules in section 13 | 20-minute review with 2 to 3 lab members before M4, plus one bioinformatician review of section 13 |
| 3 | Restricted-data scope: what kind, whose, under what terms? | Drives access-control design, possibly a database | Not built; layout and gate designed now | Decide before the first restricted dataset is proposed |
| 4 | R2 + DuckDB-Wasm range-request feasibility (CORS, caching, latency) | Core architecture claim | Works without a Worker | M2 spike |
| 5 | Publisher model | Roles, review workflow, CMS tier | Only Richard (confirmed) | Revisit if contributors join |
| 6 | Real query transfer volumes and browser memory limits on target devices | Determines when server compute is needed | Recipes stay under 50 MB | M4 measurements on 3 devices |
| 7 | Standardization strategy: own manifest vs Frictionless vs Croissant/DataCite | Affects how "standardized" is communicated and interoperability | Frictionless-compatible manifest plus DataCite-style citation | Revisit at the second dataset |
| 8 | Domain name and brand | Cosmetic, but needed for launch | TBD | Pick before M1 |
| 9 | Sanity free-tier limits at time of use | Cost only | Free for one editor | Check at M5 |
| 11 | Employer or institution IP rules for a side project that may be commercialized | Could block or complicate commercialization | Unknown | Read your employment contract or ask HR before launch (section 15) |
| 12 | Which combinatorial and drug + CRISPR sources exist and under which licences | Determines the second and third source and whether the model fits | The unified model in 12.2 fits them | Source survey in R1 |
| 10 | Notion archive | Convenience | Spec lives in project files; copy to Notion Home when the connector is back | Later |


---

## 12. Unified CRISPR data model (the core of the product)

### 12.1 Principle
The unit users explore is a **collection** (`crispr-human`), not a source file. Each source (BioGRID ORCS now, others later) is converted by its own adapter into the same tables. Every row keeps `source_dataset` and `source_screen_id`, so provenance is never lost. A dataset page still exists per source (licence, citation, version), but search, comparison and reproducibility work across the whole collection.

### 12.2 Tables (logical model; names are proposals)
| Table | One row per | Key fields |
|---|---|---|
| `studies` | publication / source release | study_id, pubmed_id, doi, title, year, source_dataset, source_release, licence_id |
| `screens` | screen as reported by the source | screen_id (ours, stable), source_screen_id, study_id, organism (human only now), cell_line_id, cell_line_label, lineage, disease_context, library_name, library_type, perturbation_type (knockout / CRISPRi / CRISPRa / base edit / other), cas_system, screen_format (**monogenic / combinatorial / drug_crispr**), phenotype, selection_type (negative / positive / sorting / other), timepoint, replicate_count, scoring_method, score_unit, hit_rule_source, metadata_quality (complete / partial / free_text_only), result_scope (all_genes / hits_only), normalization_status (anchored / rank_only / robust_z / not_comparable), n_ceg_present, n_neg_present |
| `conditions` | treatment or control arm of a screen | condition_id, screen_id, role (control / treatment), agent_label, agent_id (ChEMBL or PubChem when mappable), dose, dose_unit, duration |
| `perturbations` | thing that was perturbed | perturbation_id, kind (single / pair), gene_a_id, gene_b_id (null for single), symbols |
| `score_defs` | native score column of a screen | screen_id, position (1 to 5), native_name, method_family, reference_contrast, signed, direction (lower_is_depleted / higher_is_depleted / unsigned / unknown), direction_evidence (documented / known_biology_test / human_confirmed / unresolved) |
| `results` | screen x perturbation | screen_id, perturbation_id, score_1..score_5 (native, never overwritten), effect_rank (Level A, 0 = most depleted), effect_scaled (Level B, null if not anchored), effect_z (Level C), source_row, p_value, fdr, hit_source (as reported), hit_standard (computed uniformly by our pipeline), interaction_score (combinatorial only, else null) |
| `gene_ids` | gene | gene_id (Entrez), hgnc_id, ensembl_id, symbol, aliases |
| `vocab_map` | normalization rule | raw_value, field, canonical_id, canonical_label, mapping_status (exact / curated / unmapped), reviewed_by, reviewed_on |

How the three screen formats fit:
- **Monogenic:** `perturbations.kind = single`, one condition or control only.
- **Combinatorial:** `kind = pair`; `results.interaction_score` holds the genetic interaction score, `effect` holds the combined effect.
- **Drug + CRISPR:** one or more `conditions` with role = treatment and an agent; comparisons between treatment and control arms are stored as their own `screens` rows linked by `parent_screen_id`.

### 12.3 Comparability rules (the bioinformatics core)
1. **Native scores are never plotted on a shared axis without a warning.** BioGRID ORCS holds scores from different methods and scales (for example log fold change, Bayes factor, z-score, MAGeCK-type scores). The pipeline keeps the native scores and adds three direction-aligned columns: `effect_rank` (Level A), `effect_scaled` (Level B) and `effect_z` (Level C), see 12.8.
2. **Default cross-screen comparison is rank-based** (percentile within screen, Spearman correlation), because ranks do not depend on score scale.
3. **Hit calls come in two forms:** `hit_source` as the source reported it, and `hit_standard` from one documented rule applied the same way to all screens. UI labels them separately. Where no standard rule can be applied (missing scores), `hit_standard` is null, not guessed.
4. **Only compare what was tested.** Comparisons use the set of genes tested in both screens, and show that number.
5. **Every comparison page shows the experiment context** (cell line, library, method, phenotype, treatment) next to the numbers.
6. **Gene identifiers** are normalized to Entrez ID (with HGNC and symbol). Symbols that cannot be mapped uniquely are flagged and excluded from cross-screen results, with a count.

### 12.4 Controlled vocabularies (verify availability and licences in M2a)
Genes: HGNC / NCBI Gene. Cell lines: Cellosaurus (and DepMap IDs where available). Lineage/disease: OncoTree or a similar controlled list. Drugs: ChEMBL or PubChem. Phenotype: free-text to a short curated list, with EFO as a later option. Mapping files are YAML in git, reviewed by diff. Unmapped values stay visible as `unmapped`, never silently dropped.

### 12.5 What I expect in the BioGRID ORCS file (verify in M2a)
From knowledge of the format, not from this file: one tab-delimited results file per screen inside the archive, with gene identifiers and symbols, one or more score columns, and a hit flag; plus a screen index with free-text and semi-structured experiment metadata (publication, cell line, library, method, phenotype, treatment). The M2a profile reports the real columns, row counts, null rates, and mapping coverage.

### 12.6 Metadata caveats users must see
Metadata from curated databases is incomplete and sometimes free text. The UI shows `metadata_quality` per screen and does not use "similar background" matching on screens marked `free_text_only`.

### 12.8 Score normalization (approved levels A, B, C)
Scores cannot be converted to one physical unit (Bayes factors, p-values and ranks discard effect size), so three levels are stored beside the native scores:
- **A, `effect_rank`:** rank percentile within the screen after direction alignment. Needs a signed score and the full gene list. Default for cross-screen comparison.
- **B, `effect_scaled`:** `(score - median_NEG) / (median_NEG - median_CEG)` using Hart NEGv1 and CEGv2: 0 = like a non-essential gene, -1 = like a core-essential gene. Only for negative-selection screens with a full gene list, a monotone score and at least 50 reference genes of each set present (1,402 of 1,952 screens in the 2.0.18 profile). Shown with the label "scale anchored on core-essential genes". The reference sets define the scale, so the known-biology check uses disjoint halves or other sets.
- **C, `effect_z`:** robust z, `(score - median) / (1.4826 x MAD)`, fallback for screens that cannot be anchored (drug, positive selection, sorting).
- **D (recompute from guide counts) is out of scope** until a source provides counts.

Direction is decided in order: documented method convention, known-biology test, human confirmation per study, else `unknown` and the `effect_*` columns stay null. Never guessed. Native scores and their definitions (`score_defs`) are shown next to every value.

### 12.7 Hooks for the future (not built now)
- Every table carries `data_type = crispr_screen`; new types (expression, proteomics, etc.) get their own collection with the same manifest format and shared entity tables (`gene_ids`, cell lines).
- Collections are published as Parquet plus JSON manifests with a machine-readable schema, which is also what an AI agent layer would need later. A cross-dataset insight agent is out of scope until the unified model is proven with at least two sources.

---

## 13. Reproducibility analysis (F22, F23)

**Question answered:** do two screens with the same or similar experimental background agree, and how strongly?

### 13.1 Matching tiers (used for suggestions in F23, and as labels in F22)
| Tier | Rule (all must match unless stated) |
|---|---|
| Identical | cell line, library, perturbation type, phenotype, selection type, treatment (or both untreated), scoring method |
| Similar | cell line, perturbation type, phenotype, treatment; library or scoring method may differ |
| Loosely related | same lineage and phenotype; cell line may differ. Shown with a "not a reproducibility test" label |

### 13.2 Metrics (v1)
1. Number of shared tested genes (required to be shown first).
2. Spearman correlation of `effect_rank` on shared genes (rank-based).
3. Overlap of `hit_standard` hits: count, Jaccard index, and hypergeometric p-value with the shared tested genes as background.
4. Recovery of reference gene sets, if licences allow (for example published core-essential and non-essential lists such as Hart et al. sets): AUC per screen, to show whether each screen separates known essentials from non-essentials. A screen that fails this is flagged as low technical quality, which explains weak agreement.
5. Plots: scatter of effect_rank (rank-rank option), overlap-by-rank curve, summary table.

### 13.3 Caveats shown on the page
Different libraries test different genes; different scoring methods weaken correlation; low shared-gene count; positive-selection screens have few hits; correlation of near-zero effects is noise; the result describes agreement, not biological truth.

### 13.4 Where it runs
Pairwise on demand in the browser (DuckDB SQL over the `results` Parquet, rank and correlation computed in SQL). Group-level summaries (F23) are **precomputed in Python at ingestion** and published as a small table, so the numbers on the catalogue are reproducible and reviewed. Cap: at most 20 screens per interactive comparison.

### 13.5 Acceptance
Browser results equal an independent Python implementation (`scipy`) to 1e-6 on at least 5 reference pairs, including one pair with partial gene overlap. A bioinformatician has signed off the methods text.

---

## 14. Bioinformatics specialist work in the agentic workflow

Coding agents write code well and still get domain details wrong silently. This project is mostly domain details. So the plan assigns specialist work explicitly.

### 14.1 Roles
| Role | Who | Responsibility |
|---|---|---|
| Product owner | Richard | Scope, merges, data releases, licence decisions |
| Domain reviewer | A bioinformatician from your lab, or an external advisor, for about 2 hours per milestone | Signs off the unified model (M2a), vocabulary mappings (M2b), comparability rules and statistics (M4b) |
| Web agent | Coding agent | Site, UI, CI, docs |
| Data agent | Coding agent (separate working rules) | Adapters, validation, standardization, Parquet, manifests, data release reports |
| Verification agent | Separate agent session, no write access to the code it checks | Writes an independent reference implementation of key calculations (Python, `scipy`) and compares to the site's results |

### 14.2 Specialist tasks (beyond collecting data)
Define score direction and standardization per method; map identifiers and resolve ambiguous symbols; curate cell line, library and phenotype mappings; define hit rules; choose and cite reference gene sets; choose similarity metrics and minimum thresholds; write user-facing method text; decide what is not comparable.

### 14.3 Known-biology checks (automated, run at every ingestion)
- Core-essential genes (ribosomal proteins, proteasome, RNA polymerase subunits and similar) are depleted (strongly negative effect) in the majority of negative-selection screens. Report the share of screens passing; flag outliers.
- Non-targeting or non-expressed genes are centered near zero.
- Score direction is consistent after standardization (spot-check 20 genes against the source).
- The row counts and gene counts per screen match the source files exactly.
Failures block the data release until a human explains them.

### 14.4 Agent rules for the data work
Never delete or silently coerce rows; always emit a rejected-rows file with reasons; every transformation is a named, tested function; every mapping change is a YAML diff; statistical code must have an independent reference test; the agent states what it could not verify.

---

## 15. Commercialization: what to change

**Short answer:** do not change the MVP build for ads. Do make four cheap design choices now so that commercialization stays possible, and decide on money after you see real traffic.

### 15.1 Check first (blocking)
1. **Licences, per source.** BioGRID ORCS under MIT allows commercial use if the copyright and licence notice is kept. Future sources often use licences that forbid commercial use (for example CC BY-NC). So `licence.allowsCommercialUse` becomes a mandatory field, and CI blocks a commercial-mode release containing a non-commercial source. Build the field in M3.
2. **Your employer or institution.** Check your contract or ask HR about side projects, IP ownership and use of your professional reputation. This is the highest-impact unknown and costs nothing to ask.
3. **Source branding.** Do not imply endorsement by BioGRID; credit them as required.
4. **Legal basics when money starts:** a legal entity or sole-proprietor registration depending on your country, VAT handling, terms of use, a disclaimer (not medical or clinical advice), a privacy policy and an imprint (many EU countries require one). I do not know your country, so this needs local advice; budget a one-off consult.

### 15.2 Options compared
| Option | Revenue potential (my assumption, unverified) | Changes needed | Downsides |
|---|---|---|---|
| Display ads (AdSense or similar) | Niche scientific traffic often earns a few euros per 1,000 pageviews. At 10,000 pageviews/month that would be tens of euros, not hundreds. Treat as an assumption to test, not a forecast | Cookie consent banner (ads use tracking cookies; this ends the "no cookies" design), consent management platform, ad slots in layout, larger JS payload, CSP changes | Hurts trust with scientists, slows pages, adds GDPR work, low income at hobby scale |
| Single relevant sponsor (a CRISPR reagent or service vendor) | A fixed monthly fee, level depends on audience size | One static, clearly labelled sponsor slot; no tracking; terms that the sponsor never influences data or results | Conflict-of-interest perception; needs a written editorial independence policy |
| Donations, grants, institutional support | Small but credible for open science | A donation link, funding page; grant applications | Irregular |
| Paid tier for private data (this uses your restricted-data requirement) | Highest long-term potential: labs compare their own private screens against the public collection | Accounts, authentication, private storage, a database, payments, GDPR processing, support. A real second product | Large build; start only after demonstrated demand |
| Paid API or bulk access, consulting, custom ingestion | Depends on demand | API layer, rate limits, contracts | Time cost |

### 15.3 Recommendation
1. MVP: no ads, cookieless analytics.
2. Build now (cheap): the `allowsCommercialUse` field and CI gate, an editorial independence and sponsorship page template, a `visibility` field, and the public/restricted bucket split already in the spec.
3. Revisit at defined triggers: at least 5,000 monthly visitors for 3 consecutive months or 3 unsolicited requests for private-data comparison. Then test one sponsor slot first, ads last.

### 15.4 Cost implication
Ads add consent tooling (free to about €15/month depending on provider) and no infrastructure. A paid tier adds a database (about €25/month), a payment processor fee, and support time.

---

## 16. Failsafes against cost escalation and review overload

### 16.1 Hard cost limits (set these up in M0, before anything else)
| Control | What it does | Note |
|---|---|---|
| Virtual payment card with a monthly limit (for example €20) used for all services | The only true hard cap: a service cannot charge more than the card allows | A declined charge can lead to suspension or a debt notice, so combine with alerts. Use a separate card for this project |
| Cloudflare billing and usage alerts (R2 operations, storage, bandwidth) at 50% and 80% of the free tier | Early warning before any charge | Check the current alert options in the dashboard; features change |
| Stay on Cloudflare free plans; do not enable paid Workers or add-ons | The free Workers plan stops at its daily limit instead of billing | Verify when you reach the point of adding a Worker |
| R2: serve public files only through a custom domain with Cloudflare caching and a rate-limit rule; set a bucket size check in the ingestion pipeline (fail above 20 GB) | Cached reads are cheap; bots and loops cannot create a large bill silently | Test caching headers in M2b |
| GitHub: public repo, Actions spending limit set to 0 | Prevents overage on Actions | Verify in billing settings |
| Sanity: free plan with no payment method attached | Cannot be billed | Confirm at M5 |
| No paid LLM API calls in the site or CI | Removes usage-based AI cost entirely. AI coding runs under your fixed-price plan | Do not create API keys for the project |
| Monthly 10-minute cost review (checklist in `docs/ops/cost-review.md`) | Catches drift | Put it in your calendar |
| Kill switch runbook (`docs/ops/kill-switch.md`) | Two steps take the data offline: disable R2 public access, unpublish the Pages site | Practice it once in M6 |
| Nightly job (M6) | Reads Cloudflare usage and emails you if above 50% of any free-tier limit | Small script, no extra service |

### 16.2 Reducing what you must review
You should not read all code. Instead:
- **Automated gates must pass before you are asked anything:** typecheck, tests, build, accessibility, Lighthouse budget, secret scan, dependency audit, data validation, known-biology checks.
- **Each PR carries a one-screen summary** in plain language: what changed, why, what could go wrong, screenshots of the preview, test results, cost impact (`none` / `yes: …`). You review that and click through the preview, not the diff.
- **Auto-merge only for:** patch/minor dependency updates that pass all checks, and CMS content publishes (they never touch code).
- **Always human:** merge of feature PRs, data releases, anything touching secrets, permissions, DNS, billing, licence fields, or the statistics.
- **Data releases are reviewed as one page:** the release report (row counts vs previous version, mapping coverage, known-biology results, rejected rows, schema diff). You approve a report, not a dataset.
- **Agent budget rules:** max about 400 changed lines per PR; one roadmap item at a time; the agent stops and asks when a task needs a new service, secret, paid feature or dependency.

---

## 17. First-timer learning path

You asked for care and an educational approach. Rules:
1. **Every milestone starts with a one-page explainer** (`docs/learning/Mx.md`): what we build, which new concepts appear (for example CDN, CORS, Parquet, range requests, CI), how to verify it yourself, and the main way it can go wrong.
2. **Every PR has a "Why this way" and "What could go wrong" paragraph** in plain language.
3. **A glossary** in `docs/glossary.md` for every term the agent introduces.
4. **You create and own all accounts** (GitHub, Cloudflare, domain registrar, Sanity), with two-factor authentication and saved recovery codes, in this order: GitHub, payment card with limit, Cloudflare, domain, Sanity. The agent never holds production credentials (section 8).
5. **Small first win:** M0 and M1 get a public page live early, so you see the whole path (code, review, preview, production, rollback) before the hard data work.
6. **Rollback practice:** in M1, deliberately deploy a broken page and roll it back, so the procedure is familiar before it matters.
