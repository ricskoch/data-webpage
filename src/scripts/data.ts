// Prototype data source: the R2 staging bucket (not a data release; see docs/learning/M2b-pipeline.md).
export const DATA_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/biogrid-orcs/0.1.0-staging/site';

export interface Screen {
  screen_id: string; study_id: string; author_label: string | null; year: number | null;
  cell_line_label: string; library_name: string; perturbation_type: string; selection_type: string;
  phenotype: string; experimental_setup: string; scoring_method: string; result_scope: string;
  normalization_status: string; direction: string | null; direction_evidence: string | null;
  known_biology_pass: boolean | null; rows: number | null; hits: number | null;
}

/** One result row for a gene: [screen index, effect_rank, effect_scaled, effect_z, hit 0/1, native score 1] */
export type GeneRow = [number, number | null, number | null, number | null, number, number | null];

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${DATA_URL}/${path}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const fmt = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined ? '–' : x.toFixed(digits);

export const label = (s: string | null | undefined) => (s ?? 'unknown').replaceAll('_', ' ');

/** Horizontal bar list as HTML, flat fills only (style guide: charts). */
export function bars(counts: Record<string, number>, total: number): string {
  const max = Math.max(...Object.values(counts));
  return Object.entries(counts).map(([k, v]) =>
    `<li><span class="bar-label">${escapeHtml(label(k))}</span>` +
    `<span class="bar" style="width:${(100 * v / max).toFixed(1)}%"></span>` +
    `<span class="bar-value">${v.toLocaleString('en')} <small>(${(100 * v / total).toFixed(0)}%)</small></span></li>`,
  ).join('');
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}
