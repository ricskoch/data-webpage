# Style guide: clean data-explorer look

Decided by the owner on 2026-10-18: the Victorian botanical look (PR #17) is dropped. The site is a
clean, modern data tool in the spirit of the DepMap Data Explorer: controls on the left, interactive
Plotly charts in the middle, details on the right. Tokens live in `src/styles/tokens.css`; use the
CSS variables, never raw hex values in pages.

## Principles
- The data is the interface: charts and tables first, decoration none.
- Every chart is interactive (hover, zoom, click-through to the underlying screen or gene).
- Plain language next to every statistic: what was compared, how many, how sure.
- Desktop first (workspace with a left control panel); the layout stacks on narrow screens.

## Colour (light / dark)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #f6f7f9 | #0f141a | page ground |
| `--surface` | #ffffff | #171d25 | cards, tables, panels |
| `--text` | #17202b | #e6ebf1 | body text |
| `--muted` | #55606e | #a3afbd | captions, labels |
| `--accent` | #1a5fd0 | #7fb0ff | links, buttons, focus ring, selection |
| `--warn` | #b42318 | #ff9a8f | warnings, "enriched" |
| `--border` | #c9d0d9 | #2f3a47 | borders only, never text |

Text must reach 4.5:1 (WCAG AA). Links stay underlined. New colours need a contrast check.

## Type
System UI font stack (no web fonts, nothing to download). Body about 15 px, labels 13 px,
numbers in tables use tabular figures and are right-aligned. Gene symbols are italic (`.gene`).

## Charts (Plotly, `src/scripts/charts.ts`)
- Plotly cartesian bundle, loaded on demand; `layout()` applies the tokens so dark mode works.
- Categorical series use `--chart-1..6` (Okabe-Ito, colour-blind safe), in order. Beyond six, use small multiples.
- Gene scores use the diverging scale `--score-low` (depleted) to `--score-high` (enriched). Always say the direction in words.
- Large scatters (thousands of genes) use `scattergl`. Give each chart container `role="group"` and an `aria-label`, and put the key finding in text next to it.
- Hover text names the screen or gene and the exact value.

## Layout (`<Base wide>` pages)
- Top bar with the site name and navigation; content up to `--max-app` wide.
- `.workspace`: left control panel (sticky, 16 rem), main canvas, optional right detail panel (from 90 rem).
- Tables: sticky header and first column, selectable rows (`aria-current`), keyboard arrows, `/` focuses search.
- Panels use `role="group"`, not `aside`, to satisfy axe's landmark rules.
- Usable at 375 px with no horizontal page scroll; touch targets at least 40 px.
