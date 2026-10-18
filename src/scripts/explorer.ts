// Grouping for the gene-page plot (F20): one row per tissue, cell line, treatment or phenotype.
export interface Group<T> { label: string; items: T[] }

const median = (v: number[]) => { const s = [...v].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

/**
 * Split `rows` by `label` (missing labels become "unknown"). With more than `max` groups the rarest are pooled into one
 * "other (n groups)" row, so every row still appears. Groups are ordered by the median of `value`, lowest first;
 * rows without a value are kept in `items` but do not count towards the order.
 */
export function groupForChart<T>(rows: T[], label: (r: T) => string | null | undefined, value: (r: T) => number | null,
  max = 12): Group<T>[] {
  const by = new Map<string, T[]>();
  for (const r of rows) { const k = label(r) || 'unknown'; (by.get(k) ?? by.set(k, []).get(k)!).push(r); }
  let groups = [...by].map(([l, items]) => ({ label: l, items }));
  if (groups.length > max) {
    groups.sort((a, b) => b.items.length - a.items.length || a.label.localeCompare(b.label, 'en'));
    const rest = groups.slice(max - 1);
    groups = [...groups.slice(0, max - 1), { label: `other (${rest.length} groups)`, items: rest.flatMap((g) => g.items) }];
  }
  const key = (g: Group<T>) => { const v = g.items.map(value).filter((x): x is number => x !== null); return v.length ? median(v) : Infinity; };
  return groups.map((g) => ({ g, k: key(g) })).sort((a, b) => a.k - b.k || a.g.label.localeCompare(b.g.label, 'en')).map((x) => x.g);
}
