// Drug page logic (F22): join the per-screen score vectors of a drug screen and its "no drug" screen.
// Vectors are {i: perturbation indices, z: robust z of the screen's native primary score, as reported}.
export interface Vector { i: number[]; z: number[] }
export type Match = 'same_study_library' | 'same_study' | 'same_cell_line';
/** [x = no-drug z, y = drug z, perturbation index] for genes present in both screens. */
export type Point = [number, number, number];

export const MATCH_TEXT: Record<Match, string> = {
  same_study_library: 'Same study and library (the paper\'s own control)',
  same_study: 'Same study, other library',
  same_cell_line: 'Other study, same cell line (lab-to-lab differences included)',
};

export function joinVectors(control: Vector, drug: Vector): Point[] {
  const zc = new Map<number, number>();
  control.i.forEach((p, k) => zc.set(p, control.z[k]));
  const out: Point[] = [];
  drug.i.forEach((p, k) => { const x = zc.get(p); if (x !== undefined) out.push([x, drug.z[k], p]); });
  return out;
}

/** Genes whose drug score sits furthest above (dir 1) or below (dir -1) the no-drug score, by y - x. */
export function topDifferences(points: Point[], dir: 1 | -1, n = 10): Point[] {
  return [...points].sort((a, b) => dir * ((b[1] - b[0]) - (a[1] - a[0])) || a[2] - b[2]).slice(0, n);
}

/** The drug name without dose, for grouping screens by drug. */
export const drugsOf = <T extends { treatment?: string | null; has_z?: boolean }>(screens: T[]) =>
  [...new Set(screens.filter((s) => s.has_z && s.treatment).map((s) => s.treatment!))].sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));

export interface DrugSummary { drug: string; screens: number; hits: number; lines: number }

/** Per drug: how many screens (with a drug) report the gene, how many call it a hit, in how many cell lines. */
export function drugSummary(results: { treatment?: string | null; cell_line_label: string; hit: number }[]): DrugSummary[] {
  const by = new Map<string, { screens: number; hits: number; lines: Set<string> }>();
  for (const r of results) {
    if (!r.treatment) continue;
    const e = by.get(r.treatment) ?? { screens: 0, hits: 0, lines: new Set<string>() };
    e.screens += 1; e.hits += r.hit ? 1 : 0; e.lines.add(r.cell_line_label);
    by.set(r.treatment, e);
  }
  return [...by].map(([drug, e]) => ({ drug, screens: e.screens, hits: e.hits, lines: e.lines.size }))
    .sort((a, b) => b.hits - a.hits || b.screens - a.screens || a.drug.localeCompare(b.drug, 'en', { sensitivity: 'base' }));
}
