// Cell line context (M3b): who each screened line is, plus per-gene expression, copy number and mutations.
// Source: DepMap Public 24Q4 and Cellosaurus (both CC BY 4.0), built by datasets/cell-line-context/build.py.
import { versioned } from './version';
export const CTX_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/cell-line-context/0.1.0-staging/site/ctx';

export interface Line {
  cellosaurus_id: string; name: string; depmap_id: string; screens: number; problematic: boolean | null;
  lineage?: string | null; disease?: string | null; subtype?: string | null; sex?: string | null;
  age?: string | null; primary_or_metastasis?: string | null;
  ploidy?: number | null; wgd?: number | null; msi_score?: number | null; aneuploidy?: number | null;
  drivers: string[];
  /** Panel genes with a loss-of-function / hotspot (gain-of-function-like) mutation; absent in files built before the split. */
  drivers_lof?: string[]; drivers_gof?: string[];
  /** False when DepMap has no mutation calls for the line (absent in files built before this field existed). */
  mutation_calls?: boolean;
}
export interface Lines { release: string; lines: Line[]; screen_line: Record<string, number> }
/** Per gene, aligned to Lines.lines: e = log2(TPM+1), c = log2(relative copy number + 1), m = [line, change, LoF, hotspot]. */
export interface GeneContext { e: (number | null)[]; c: (number | null)[]; m: [number, string, number, number][] }

export interface LineGene { expression: number | null; copyNumber: number | null; mutation: string | null }

/** What this gene looks like in one cell line. */
export function geneInLine(g: GeneContext | undefined, line: number): LineGene {
  if (!g) return { expression: null, copyNumber: null, mutation: null };
  const muts = g.m.filter((m) => m[0] === line).map((m) => m[1] + (m[3] ? ' (hotspot)' : m[2] ? ' (loss of function)' : ''));
  return { expression: g.e[line] ?? null, copyNumber: g.c[line] ?? null, mutation: muts.length ? muts.join(', ') : null };
}

/** Plain-language copy number. DepMap stores log2(ratio + 1), so 1 = the line's normal copy number.
 *  Display bands only (not a statistical call): <0.25x deep loss, <0.75x loss, >1.5x gain, >3x amplified. */
export function copyLabel(v: number | null): string | null {
  if (v === null) return null;
  const ratio = 2 ** v - 1;
  return ratio < 0.25 ? 'deep loss' : ratio < 0.75 ? 'loss' : ratio > 3 ? 'amplified' : ratio > 1.5 ? 'gain' : 'normal';
}

/** Plain-language expression: log2(TPM+1) below 1 means under 1 transcript per million, i.e. essentially off. */
export function expressionLabel(v: number | null): string | null {
  if (v === null) return null;
  return v < 1 ? 'off' : v < 3 ? 'low' : v < 6 ? 'medium' : 'high';
}

export async function getCtx<T>(path: string): Promise<T> {
  const res = await fetch(versioned(`${CTX_URL}/${path}`));
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

/** Context is optional: pages keep working (without the extra columns) if it is not published yet. */
let linesOnce: Promise<Lines | null> | undefined;
export function loadLines(): Promise<Lines | null> {
  linesOnce ??= getCtx<Lines>('lines.json').catch(() => null);
  return linesOnce;
}

export async function loadGene(pid: string, shard: number): Promise<GeneContext | undefined> {
  try { return (await getCtx<Record<string, GeneContext>>(`g/${String(shard).padStart(4, '0')}.json`))[pid]; }
  catch { return undefined; }
}

/** Attribution required by CC BY 4.0, shown wherever context data appears. */
export function credit(l: Lines): string {
  return `<small>Cell line context: ${String(l.release ?? 'DepMap').replace(/[<>&]/g, '')} (Broad Institute) and Cellosaurus (SIB), both CC BY 4.0. `
    + `Tissue and mutations describe the cell line, not the screen; ${l.lines.length} screened lines are profiled.</small>`;
}
