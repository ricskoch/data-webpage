// Biological workflow 2 of the M3 plan: "Is gene X a dependency only when gene Y is mutated?"
// Method approved by Richard on 2026-10-11:
// - one value per cell line: the median of that line's screens on the essential-gene scale (0 = non-essential,
//   -1 = core-essential), so a line screened ten times counts once;
// - Y-mutant lines vs Y-wild-type lines: difference of medians (mutant minus wild-type) with a percentile
//   bootstrap 95% interval (seeded, so the same question always gives the same answer);
// - two-sided Mann-Whitney U test, normal approximation with tie and continuity correction (as SciPy's
//   mannwhitneyu with method="asymptotic");
// - at least MIN_LINES lines per group, otherwise the question is reported as not testable.
// No imports, so node can run this file directly for the independent SciPy reference test
// (tests/reference/test_workflow_reference.py) and the known-biology check (tests/reference/validate_recipe_live.mjs).

export const MIN_LINES = 5;
export const RESAMPLES = 4000;

export function median(xs: number[]): number {
  if (!xs.length) return NaN;
  const s = [...xs].sort((a, b) => a - b), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Complementary error function, fractional error below 1.2e-7 (Numerical Recipes erfcc). */
function erfc(x: number): number {
  const z = Math.abs(x), t = 1 / (1 + 0.5 * z);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
    t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? r : 2 - r;
}

/** U for the first sample and the two-sided p-value. p is NaN when every value is tied. */
export function mannWhitney(a: number[], b: number[]): { u: number; p: number } {
  const all = [...a.map((v) => [v, 0]), ...b.map((v) => [v, 1])].sort((x, y) => x[0] - y[0]);
  const n = all.length, na = a.length, nb = b.length;
  let rankA = 0, ties = 0;
  for (let i = 0; i < n;) {
    let j = i;
    while (j + 1 < n && all[j + 1][0] === all[i][0]) j++;
    const t = j - i + 1, rank = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) if (all[k][1] === 0) rankA += rank;
    ties += t ** 3 - t;
    i = j + 1;
  }
  const u = rankA - (na * (na + 1)) / 2;
  const s = Math.sqrt(((na * nb) / 12) * (n + 1 - ties / (n * (n - 1))));
  const z = (Math.max(u, na * nb - u) - (na * nb) / 2 - 0.5) / s;
  return { u, p: s > 0 ? Math.min(1, erfc(z / Math.SQRT2)) : NaN };
}

/** Small seeded generator (mulberry32), so the interval does not change between page loads. */
function rng(seed: number): () => number {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Linear-interpolation quantile of sorted values (the numpy default). */
function quantile(sorted: number[], q: number): number {
  const h = (sorted.length - 1) * q, lo = Math.floor(h);
  return sorted[lo] + (h - lo) * ((sorted[lo + 1] ?? sorted[lo]) - sorted[lo]);
}

/** Percentile bootstrap 95% interval for median(a) - median(b), resampling each group separately. */
export function bootstrapDiff(a: number[], b: number[], resamples = RESAMPLES, seed = 1): [number, number] {
  const r = rng(seed), pick = (xs: number[]) => xs.map(() => xs[Math.floor(r() * xs.length)]);
  const diffs = Array.from({ length: resamples }, () => median(pick(a)) - median(pick(b))).sort((x, y) => x - y);
  return [quantile(diffs, 0.025), quantile(diffs, 0.975)];
}

export interface LineValue { line: number; value: number; screens: number }
export interface Comparison {
  mutant: LineValue[]; wildtype: LineValue[]; testable: boolean;
  diff: number; ci: [number, number] | null; u: number | null; p: number | null;
}

/** Collapse screens to one value per line, split by mutation status, and compare.
 *  `include(line)` says whether a line may enter the comparison (has mutation calls, not a flagged line). */
export function dependencyByMutation(perScreen: { line: number; value: number }[], mutant: Set<number>,
  include: (line: number) => boolean): Comparison {
  const byLine = new Map<number, number[]>();
  for (const { line, value } of perScreen) {
    if (include(line) && Number.isFinite(value)) byLine.set(line, [...(byLine.get(line) ?? []), value]);
  }
  const values = [...byLine].map(([line, v]) => ({ line, value: median(v), screens: v.length }));
  const mut = values.filter((v) => mutant.has(v.line)), wt = values.filter((v) => !mutant.has(v.line));
  const a = mut.map((v) => v.value), b = wt.map((v) => v.value);
  const diff = median(a) - median(b);
  if (a.length < MIN_LINES || b.length < MIN_LINES) return { mutant: mut, wildtype: wt, testable: false, diff, ci: null, u: null, p: null };
  const { u, p } = mannWhitney(a, b);
  return { mutant: mut, wildtype: wt, testable: true, diff, ci: bootstrapDiff(a, b), u, p };
}

/** Plain-language reading, based on whether the 95% interval excludes zero. `names` labels the two groups. */
export function verdict(c: Comparison, x: string, y: string, names = { a: `${y}-mutant`, b: 'wild-type' }): string {
  if (!c.testable) return `Not enough lines to compare (needs at least ${MIN_LINES} ${names.a} and ${MIN_LINES} ${names.b} lines).`;
  if (c.ci![0] > 0) return `Knocking out ${x} hurts ${names.a} lines less (or helps them more) than ${names.b} lines.`;
  if (c.ci![1] < 0) return `Knocking out ${x} hurts ${names.a} lines more (or helps them less) than ${names.b} lines.`;
  return `No clear difference: ${x} behaves about the same in ${names.a} and ${names.b} lines.`;
}
