// Data overview (F20): which kinds of treatment the collection holds, and which drugs were screened in which cell lines.
// Pure functions over the screen list; the page draws them.
interface S { screen_id: string; study_id: string; treatment?: string | null; treatment_category?: string | null; cell_line_label: string; rows: number | null }

/** Plain-language names for the categories of treatment_classes.yaml, in display order. */
export const KIND_TEXT: Record<string, string> = {
  untreated: 'No treatment',
  drug_compound: 'Drug or compound',
  genetic_background: 'Genetic background',
  condition_change: 'Change of conditions',
  culture_format: 'Culture format',
  biological_agent: 'Virus, bacterium or other cells',
  unclassified: 'Not yet sorted',
};

/** Screens per kind, in KIND_TEXT order; a screen without a category counts as not yet sorted. */
export function kindCounts(screens: S[]): Record<string, number> {
  const n: Record<string, number> = {};
  for (const s of screens) { const k = KIND_TEXT[s.treatment_category ?? ''] ?? KIND_TEXT.unclassified; n[k] = (n[k] ?? 0) + 1; }
  const order = Object.values(KIND_TEXT);
  return Object.fromEntries(Object.entries(n).sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0])));
}

export interface Cell { screens: number; studies: number; genes: number }
export interface Coverage {
  drugs: { drug: string; screens: number; lines: number }[];
  lines: { line: string; screens: number; drugs: number }[];
  /** key "drug|cell line" */
  cells: Map<string, Cell>;
}

/** Drug/compound screens only. `genes` is the largest gene count among the screens of that drug and cell line. */
export function drugCoverage(screens: S[]): Coverage {
  const acc = new Map<string, { screens: number; studies: Set<string>; genes: number }>();
  const byDrug = new Map<string, { screens: number; lines: Set<string> }>();
  const byLine = new Map<string, { screens: number; drugs: Set<string> }>();
  for (const s of screens) {
    if (s.treatment_category !== 'drug_compound' || !s.treatment) continue;
    const key = `${s.treatment}|${s.cell_line_label}`;
    const c = acc.get(key) ?? { screens: 0, studies: new Set<string>(), genes: 0 };
    c.screens += 1; c.studies.add(s.study_id); c.genes = Math.max(c.genes, s.rows ?? 0); acc.set(key, c);
    const d = byDrug.get(s.treatment) ?? { screens: 0, lines: new Set<string>() };
    d.screens += 1; d.lines.add(s.cell_line_label); byDrug.set(s.treatment, d);
    const l = byLine.get(s.cell_line_label) ?? { screens: 0, drugs: new Set<string>() };
    l.screens += 1; l.drugs.add(s.treatment); byLine.set(s.cell_line_label, l);
  }
  const by = (a: string, b: string) => a.localeCompare(b, 'en', { sensitivity: 'base' });
  return {
    drugs: [...byDrug].map(([drug, e]) => ({ drug, screens: e.screens, lines: e.lines.size })).sort((a, b) => b.screens - a.screens || by(a.drug, b.drug)),
    lines: [...byLine].map(([line, e]) => ({ line, screens: e.screens, drugs: e.drugs.size })).sort((a, b) => b.screens - a.screens || by(a.line, b.line)),
    cells: new Map([...acc].map(([k, c]) => [k, { screens: c.screens, studies: c.studies.size, genes: c.genes }])),
  };
}
