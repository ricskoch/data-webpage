// Ways to split cell lines into two groups for the biological workflow in workflow.ts (the method is the same for every split,
// as approved on 2026-10-11): by a gene's mutation, expression or copy number, by whole-genome doubling, or by tissue.
// Lines in neither group, and lines Cellosaurus flags as misidentified or contaminated, are left out.
import { copyLabel, type GeneContext, type Lines } from './context.ts';

export type GroupKind = 'mutation' | 'mutlof' | 'mutgof' | 'expression' | 'copy' | 'deeploss' | 'gain' | 'wgd' | 'tissue';
export interface Grouping { group: Set<number>; include: (line: number) => boolean; a: string; b: string }

/** Expression bands match expressionLabel: off is log2(TPM+1) < 1, expressed is 3 or more (medium or high). */
export const OFF_BELOW = 1;
export const EXPRESSED_FROM = 3;

export const KIND_LABELS: Record<GroupKind, string> = {
  mutation: 'a mutation in a gene', mutlof: 'a loss-of-function mutation in a gene', mutgof: 'a hotspot (gain-of-function-like) mutation in a gene', expression: 'a gene being switched off', copy: 'a gene losing copies', deeploss: 'a gene lost almost completely', gain: 'a gene gaining copies',
  wgd: 'whole-genome doubling', tissue: 'tissue',
};
export const NEEDS_GENE: GroupKind[] = ['mutation', 'mutlof', 'mutgof', 'expression', 'copy', 'deeploss', 'gain'];

export function makeGrouping(kind: GroupKind, lines: Lines, y: string, yctx?: GeneContext, tissue?: string): Grouping {
  const all = lines.lines.map((_, i) => i);
  const fine = (l: number) => !lines.lines[l].problematic;
  const pick = (test: (l: number) => boolean) => new Set(all.filter(test));
  switch (kind) {
    case 'mutation': // lines with no mutation calls at all must not count as wild-type
      return { group: new Set((yctx?.m ?? []).map((m) => m[0])), a: `${y}-mutant`, b: 'wild-type',
        include: (l) => fine(l) && lines.lines[l].mutation_calls !== false };
    case 'mutlof':
    case 'mutgof': { // same classes as the precomputed associations: LoF = DepMap LikelyLoF, hotspot = Hotspot and not LikelyLoF
      const lof = new Set<number>(), hot = new Set<number>(), any = new Set<number>();
      for (const [l, , isLof, isHot] of yctx?.m ?? []) { any.add(l); if (isLof) lof.add(l); else if (isHot) hot.add(l); }
      const own = kind === 'mutlof' ? (l: number) => lof.has(l) && !hot.has(l) : (l: number) => hot.has(l) && !lof.has(l);
      return { group: pick(own), a: kind === 'mutlof' ? `${y} loss of function` : `${y} hotspot mutation`, b: 'wild-type',
        include: (l) => fine(l) && lines.lines[l].mutation_calls !== false && (own(l) || !any.has(l)) };
    }
    case 'expression': {
      const e = (l: number) => yctx?.e[l] ?? null;
      return { group: pick((l) => e(l) !== null && e(l)! < OFF_BELOW), a: `${y}-off`, b: `${y}-expressed`,
        include: (l) => fine(l) && e(l) !== null && (e(l)! < OFF_BELOW || e(l)! >= EXPRESSED_FROM) };
    }
    case 'copy': {
      const c = (l: number) => copyLabel(yctx?.c[l] ?? null);
      const lost = (l: number) => c(l) === 'loss' || c(l) === 'deep loss';
      return { group: pick(lost), a: `${y}-loss`, b: `${y}-normal copy number`, include: (l) => fine(l) && (lost(l) || c(l) === 'normal') };
    }
    case 'deeploss': {
      const c = (l: number) => copyLabel(yctx?.c[l] ?? null);
      return { group: pick((l) => c(l) === 'deep loss'), a: `${y}-deep loss`, b: `${y}-normal copy number`,
        include: (l) => fine(l) && (c(l) === 'deep loss' || c(l) === 'normal') };
    }
    case 'gain': {
      const c = (l: number) => copyLabel(yctx?.c[l] ?? null);
      const gained = (l: number) => c(l) === 'gain' || c(l) === 'amplified';
      return { group: pick(gained), a: `${y}-gained`, b: `${y}-normal copy number`, include: (l) => fine(l) && (gained(l) || c(l) === 'normal') };
    }
    case 'wgd': {
      const w = (l: number) => lines.lines[l].wgd;
      return { group: pick((l) => (w(l) ?? 0) > 0.5), a: 'genome-doubled', b: 'not genome-doubled',
        include: (l) => fine(l) && w(l) !== null && w(l) !== undefined };
    }
    case 'tissue':
      return { group: pick((l) => lines.lines[l].lineage === tissue), a: `${tissue}`, b: 'all other tissues',
        include: (l) => fine(l) && !!lines.lines[l].lineage };
  }
}
