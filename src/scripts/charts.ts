// Plotly charts with the site's colours (F6). Plotly is loaded on demand so pages without charts do not pay for it.
// The cartesian bundle has scatter, scattergl (WebGL, for 18k-gene scatters), bar, box, violin, heatmap and histogram.
export type Plot = { data: unknown[]; layout?: Record<string, unknown>; config?: Record<string, unknown> };

let lib: Promise<any> | undefined;
export const loadPlotly = () => (lib ??= import('plotly.js-cartesian-dist-min').then((m: any) => m.default ?? m));

/** Read the CSS tokens at call time, so dark mode and later token changes apply without code changes. */
export function palette() {
  const css = getComputedStyle(document.documentElement);
  const v = (n: string) => css.getPropertyValue(n).trim();
  return {
    text: v('--text'), muted: v('--muted'), surface: v('--surface'), border: v('--border'), soft: v('--border-soft'),
    accent: v('--accent'), warn: v('--warn'), low: v('--score-low'), mid: v('--score-mid'), high: v('--score-high'),
    series: [1, 2, 3, 4, 5, 6].map((i) => v(`--chart-${i}`)), font: v('--font-body'),
  };
}

/** Layout defaults: transparent background, thin axes, token colours. Pass overrides to merge on top (one level deep). */
export function layout(over: Record<string, any> = {}): Record<string, any> {
  const p = palette();
  const axis = { gridcolor: p.soft, zerolinecolor: p.border, linecolor: p.border, tickcolor: p.border, automargin: true,
    title: { font: { size: 12, color: p.muted } }, tickfont: { size: 11, color: p.muted } };
  const base: Record<string, any> = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { family: p.font, color: p.text, size: 12 },
    margin: { l: 48, r: 16, t: 28, b: 44 }, xaxis: axis, yaxis: axis, showlegend: false, hovermode: 'closest',
    hoverlabel: { bgcolor: p.surface, bordercolor: p.border, font: { color: p.text } },
  };
  const out: Record<string, any> = { ...base, ...over };
  for (const k of ['xaxis', 'yaxis']) out[k] = { ...axis, ...(over[k] ?? {}) };
  return out;
}

export const config = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'] };

/** Draw (or redraw) a chart in `el`. Returns the Plotly graph div, which emits plotly_click and plotly_hover. */
export async function draw(el: HTMLElement, data: unknown[], over: Record<string, any> = {}, cfg: Record<string, any> = {}): Promise<any> {
  const Plotly = await loadPlotly();
  await Plotly.react(el, data, layout(over), { ...config, ...cfg });
  return el;
}

/** Horizontal bar chart of counts, largest at the top. */
export function barTrace(counts: Record<string, number>, color = 'var(--chart-1)') {
  const entries = Object.entries(counts).sort((a, b) => a[1] - b[1]);
  const c = color.startsWith('var(') ? palette().series[0] : color;
  return { type: 'bar', orientation: 'h', x: entries.map((e) => e[1]), y: entries.map((e) => e[0].replaceAll('_', ' ')),
    marker: { color: c }, hovertemplate: '%{y}: %{x:,}<extra></extra>' };
}

/** Like draw, for charts with thousands of points: tries WebGL (`scattergl`) and falls back to plain SVG (`scatter`) if the browser has none. */
export async function drawPoints(el: HTMLElement, build: (type: 'scattergl' | 'scatter') => unknown[], over: Record<string, any> = {}, cfg: Record<string, any> = {}): Promise<any> {
  try { return await draw(el, build('scattergl'), over, cfg); } catch { return draw(el, build('scatter'), over, cfg); }
}
