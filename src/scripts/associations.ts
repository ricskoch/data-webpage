// Precomputed associations (redesign step 3, F23): which genes differ in dependency between two groups of cell lines.
// Built by datasets/associations/build.py; the method is described on the page and in datasets/associations/README.md.
import { versioned } from './version';
export const ASSOC_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/associations/0.1.0-staging/site/assoc';

export interface Question { id: string; label: string; a: string; b: string; file: string; lines_a: number; lines_b: number; tested: number; significant: number }
export interface Index { release: string | null; min_lines: number; fdr: number; genes: string[]; questions: Question[] }
/** Parallel arrays, one entry per gene tested: g = index into Index.genes, d = median(A) - median(B), p, q, lines per group. */
export interface Result { g: number[]; d: number[]; p: (number | null)[]; q: (number | null)[]; na: number[]; nb: number[] }
/** more = more essential in group A (negative effect), less = less essential in A, ns = not called. */
export type Call = 'more' | 'less' | 'ns';
export interface Hit { gene: string; d: number; p: number | null; q: number; na: number; nb: number; call: Call }

export async function getAssoc<T>(path: string): Promise<T> {
  const res = await fetch(versioned(`${ASSOC_URL}/${path}`));
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

/** A gene is called when q is at most `fdr` and the effect is at least `minEffect` in size. */
export function callOf(d: number, q: number | null, fdr: number, minEffect: number): Call {
  if (q === null || q > fdr || Math.abs(d) < minEffect) return 'ns';
  return d < 0 ? 'more' : 'less';
}

/** Called genes, smallest q first, ties by larger effect. `only` limits to one direction. */
export function topHits(r: Result, genes: string[], fdr: number, minEffect: number, limit: number, only?: Call): Hit[] {
  const hits: Hit[] = [];
  r.g.forEach((gi, i) => {
    const q = r.q[i], call = callOf(r.d[i], q, fdr, minEffect);
    if (call !== 'ns' && (!only || call === only)) hits.push({ gene: genes[gi], d: r.d[i], p: r.p[i], q: q!, na: r.na[i], nb: r.nb[i], call });
  });
  return hits.sort((x, y) => x.q - y.q || Math.abs(y.d) - Math.abs(x.d) || x.gene.localeCompare(y.gene, 'en')).slice(0, limit);
}

/** The precomputed calls of one gene: [question number, effect, q], strongest first. */
export interface ByGene { questions: string[]; fdr: number; min_effect: number; genes: Record<string, [number, number, number][]> }

export type WorkflowSpec = { kind: 'mutation' | 'mutlof' | 'mutgof'; gene: string } | { kind: 'tissue'; tissue: string };

/** The biological workflow on /gene that asks the same question as a precomputed one (ids are `mut:GENE`, `mutlof:GENE`, `mutgof:GENE` or `tissue:NAME`). */
export function workflowOf(id: string): WorkflowSpec | null {
  const [kind, ...rest] = id.split(':'), name = rest.join(':');
  if (!name) return null;
  return kind === 'mut' ? { kind: 'mutation', gene: name } : kind === 'mutlof' ? { kind: 'mutlof', gene: name } : kind === 'mutgof' ? { kind: 'mutgof', gene: name } : kind === 'tissue' ? { kind: 'tissue', tissue: name } : null;
}

/** Link to the gene explorer with the matching workflow already run, e.g. /gene?g=EGFR&by=mutation&y=KRAS. */
export function geneLink(gene: string, questionId: string): string {
  const w = workflowOf(questionId), g = `/gene?g=${encodeURIComponent(gene)}`;
  return !w ? g : w.kind !== 'tissue' ? `${g}&by=${w.kind}&y=${encodeURIComponent(w.gene)}` : `${g}&by=tissue&t=${encodeURIComponent(w.tissue)}`;
}
