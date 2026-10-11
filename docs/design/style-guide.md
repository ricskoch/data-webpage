# Style guide: botanical plate look

Approved by the owner on 2026-10-11 (preview: "Botanical style preview" artifact in the project).
Every page, chart, icon and future item follows this guide. Tokens live in `src/styles/tokens.css`;
use the CSS variables, never raw hex values in pages.

## Idea in one line
A 19th-century natural-history plate (parchment, ink, watercolour) used to show modern molecular
data. The decoration is old; the data presentation is strict and modern.

## Colour
| Token | Light | Dark | Use | Contrast on ground (light / dark) |
|---|---|---|---|---|
| `--bg` | #f3ead7 parchment | #1d1913 | page ground | - |
| `--surface` | #fbf6ea vellum | #27211a | cards, tables, notices | - |
| `--text` | #2b2118 ink | #ede3cf | body text | 13.2 / 13.7 |
| `--muted` | #5e4b37 sepia | #c4b497 | captions, secondary text | 6.9 / 8.6 |
| `--accent` | #3b5b28 sap green | #a8c48a | links, buttons, focus ring | 6.5 / 9.1 |
| `--warn` | #8e3b26 madder | #e59b82 | warnings, "enriched" | 6.3 / 7.8 |
| `--info` | #2f4a6b woad | #a3bcdb | info, "depleted" | 7.6 / 9.0 |
| `--border` | #b9a47e pencil | #5a4c39 | rules and borders only, never text | 2.0 / 2.1 |

Rules: text must reach 4.5:1 (WCAG AA). Links stay underlined so they never rely on colour alone.
New colours need a contrast check before use.

## Type
- **Headings:** Playfair Display, weight 600. A Didone like Victorian title pages. Headings only.
- **Body, tables, labels:** Source Serif 4. Made for screen reading; has small capitals and tabular figures.
- Both are SIL Open Font License, self-hosted from `public/fonts/` (Latin subset, variable files, licences beside them) and declared in `src/styles/fonts.css`. Never load fonts from Google Fonts or another third party.
- Labels and table headers: small capitals (`font-variant-caps: all-small-caps`, letter-spacing 0.1em).
- Gene symbols: italic (`.gene`). Numbers in tables: tabular figures, right-aligned (`td.num`).
- Captions: italic sepia, numbered "Fig. n." / "Table n.".

## Icons
- Molecular schemes only: no plants or other organisms. Current set in `public/icons/`:
  `cas9` (logo, favicon), `helix` (screens, data), `lens` (search, gene lookup), `align`
  (comparison, reproducibility), `plasmid` (downloads, docs), `sgrna` (methods, learning), `rule` (section divider).
- Style: SVG, 96 x 96 viewBox, translucent pigment washes with darker pooled edges and paper grain
  (SVG filters), under a slightly wavering ink line (#3a2a1c, 1.6 px). Pigments: woad #5b86b4,
  ochre #d29a45, madder #b5543a, green #6e9a48.
- All icons are original work for this project. Never trace or copy scanned book plates or other
  people's illustrations without a checked licence. Keep each file under about 5 KB.
- Give every icon `class="icon"`: in dark mode CSS flips its lightness so the ink line reads light.
- Decorative icons get `alt=""`; an icon that carries meaning gets a real `alt`.

## Charts
- Flat fills only. The watercolour texture is decoration and must never sit on data marks.
- Categorical series: `--chart-1` to `--chart-6`, in order. The first two differ in lightness as well
  as hue, which keeps them apart for colour-blind readers. Beyond six series, use small multiples.
- Gene scores: diverging scale `--score-low` (depleted, blue) to `--score-mid` (no effect) to
  `--score-high` (enriched, madder). Always label the direction in words.
- Thin ink axes, few or no gridlines, body font for labels, numbered italic caption.
- Charts read the CSS variables at render time so dark mode works.

## Components
- **Notice:** vellum box with a double pencil rule, like a specimen label (`.notice`).
- **Plates:** icon cards in a responsive grid (`.plates`).
- **Tables:** inside `.table-box` (scrolls sideways on phones), ink rule under the header. Give the box `tabindex="0" role="region" aria-label="…"` so keyboard users can scroll it (axe rule scrollable-region-focusable).
- **Divider:** `rule.svg` (`.rule`) between major sections, at most once or twice a page.

## Layout and accessibility
- Reading width `--max` (46rem); header and footer use `--max-wide`.
- Usable at 375 px wide with no horizontal scroll; touch targets at least 44 px tall.
- Respect dark mode through the tokens; do not add a separate dark stylesheet.
