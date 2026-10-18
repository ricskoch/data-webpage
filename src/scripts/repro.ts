// Reproducibility of repeated drug screens (F20): how well two screens of the same drug in the same cell line agree.
// Built by datasets/reproducibility/reproducibility.py (method chosen by Richard 2026-10-18, see its README).
export const REPRO_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/reproducibility/0.1.0-staging/site/repro';

/** [drug, cell line, screen index a, screen index b, shared genes, rho, overlap of the 200 strongest genes, expected overlap by chance, same study 0/1] */
export type Pair = [string, string, number, number, number, number, number, number, number];
export interface Repro { top: number; min_shared: number; pairs: Pair[] }

export async function getRepro(): Promise<Repro> {
  const res = await fetch(`${REPRO_URL}/pairs.json`);
  if (!res.ok) throw new Error(`pairs.json: HTTP ${res.status}`);
  return res.json() as Promise<Repro>;
}

export type Band = 'agree' | 'partly' | 'weak';
export const BAND_TEXT: Record<Band, string> = { agree: 'agree well', partly: 'partly agree', weak: 'barely agree' };

/** rho of 0.5 or more reads as agreeing, 0.2 up to 0.5 as partly, below 0.2 as barely. */
export const bandOf = (rho: number): Band => (rho >= 0.5 ? 'agree' : rho >= 0.2 ? 'partly' : 'weak');

const median = (v: number[]) => { const s = [...v].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

export interface Summary { pairs: number; combos: number; median: number | null; bands: Record<Band, number> }

export function summarize(pairs: Pair[]): Summary {
  const bands: Record<Band, number> = { agree: 0, partly: 0, weak: 0 };
  for (const p of pairs) bands[bandOf(p[5])] += 1;
  return { pairs: pairs.length, combos: new Set(pairs.map((p) => `${p[0]}|${p[1]}`)).size, median: pairs.length ? median(pairs.map((p) => p[5])) : null, bands };
}

/** How many times more of the strongest genes the two screens share than two random screens would. */
export const overChance = (p: Pair) => (p[7] > 0 ? p[6] / p[7] : 0);
