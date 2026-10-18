// Prototype data source: the R2 staging bucket (not a data release; see docs/learning/M2b-pipeline.md).
import { versioned } from './version';
import { loadLines } from './context';
export const DATA_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/biogrid-orcs/0.1.0-staging/site';

export interface Screen {
  screen_id: string; study_id: string; author_label: string | null; year: number | null;
  cell_line_label: string; library_name: string; perturbation_type: string; selection_type: string;
  phenotype: string; experimental_setup: string; scoring_method: string; result_scope: string;
  normalization_status: string; direction: string | null; direction_evidence: string | null;
  known_biology_pass: boolean | null; rows: number | null; hits: number | null;
  /** Condition as the source names it (drug, virus, toxin...), null for untreated screens. */
  treatment?: string | null; treatment_dose?: string | null; treatment_duration?: string | null; treatment_category?: string | null;
  /** Display names from the export (cell line like MDAMB231, drug like Olaparib); absent in older exports. */
  cell_line_display?: string; treatment_display?: string | null;
  /** Source labels, kept when the display names replace cell_line_label and treatment on load. */
  cell_line_raw?: string; treatment_raw?: string | null;
  /** Drug page: native name and column of the score the per-screen vector is built from; has_z = vector published. */
  primary_score_name?: string | null; primary_score_position?: number | null; has_z?: boolean;
}

/** "Olaparib (5.0 µM)", "Olaparib", or null when the screen names no condition. */
export function treatmentLabel(s: Screen): string | null {
  if (!s.treatment) return null;
  return s.treatment_dose ? `${s.treatment} (${s.treatment_dose})` : s.treatment;
}

/** One result row for a gene: [screen index, effect_rank, effect_scaled, effect_z, hit 0/1, native score 1] */
export type GeneRow = [number, number | null, number | null, number | null, number, number | null];

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(versioned(`${DATA_URL}/${path}`));
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

/**
 * Swaps the display names in for the source labels, so pages show one spelling. Cell lines are only merged when they are
 * the same line (same Cellosaurus ID, else the same source label); lines that merely look alike after tidying keep their
 * source label in brackets. Falls back to the source label when a display name is missing.
 */
export function applyDisplayNames(screens: Screen[], idOf: (s: Screen) => string | undefined = () => undefined): Screen[] {
  const keyOf = (s: Screen) => idOf(s) ?? `label:${s.cell_line_raw}`;
  for (const s of screens) {
    if (s.cell_line_raw !== undefined) continue;
    s.cell_line_raw = s.cell_line_label; s.treatment_raw = s.treatment;
  }
  const keys = new Map<string, Set<string>>(); // display name -> distinct lines that carry it
  for (const s of screens) {
    if (!s.cell_line_display) continue;
    const k = keys.get(s.cell_line_display) ?? new Set<string>();
    k.add(keyOf(s)); keys.set(s.cell_line_display, k);
  }
  for (const s of screens) {
    if (s.cell_line_display) s.cell_line_label = keys.get(s.cell_line_display)!.size > 1 ? `${s.cell_line_display} (${s.cell_line_raw})` : s.cell_line_display;
    if (s.treatment_raw && s.treatment_display) s.treatment = s.treatment_display;
  }
  return screens;
}

export async function getScreens(): Promise<Screen[]> {
  const [screens, lines] = await Promise.all([getJSON<Screen[]>('screens.json'), loadLines()]);
  return applyDisplayNames(screens, (s) => {
    const i = lines?.screen_line[String(s.screen_id)];
    return i === undefined ? undefined : lines!.lines[i].cellosaurus_id || lines!.lines[i].depmap_id || undefined;
  });
}

export const fmt = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined ? '–' : x.toFixed(digits);

export const label = (s: string | null | undefined) => (s ?? 'unknown').replaceAll('_', ' ');

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}
