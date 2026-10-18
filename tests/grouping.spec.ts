import { test, expect } from '@playwright/test';
import { makeGrouping } from '../src/scripts/grouping';
import type { GeneContext, Lines } from '../src/scripts/context';

// Pure-logic tests for the ways lines are split into two groups (biological workflow 2, other splits).
const line = (o: object) => ({ cellosaurus_id: 'CVCL_x', name: 'x', depmap_id: 'ACH-1', screens: 1, problematic: false, drivers: [], ...o });
const lines: Lines = {
  release: 'test', screen_line: {},
  lines: [
    line({ lineage: 'Lung', wgd: 1, mutation_calls: true }),            // 0: mutated, expression off, copy loss
    line({ lineage: 'Lung', wgd: 0, mutation_calls: true }),            // 1: wild-type, expressed, normal
    line({ lineage: 'Skin', wgd: null, mutation_calls: false }),        // 2: no mutation calls
    line({ lineage: 'Skin', wgd: 0, mutation_calls: true, problematic: true }), // 3: flagged line
    line({ lineage: null, wgd: 0, mutation_calls: true }),              // 4: expression low (neither group), copy gain
  ],
};
const g: GeneContext = { e: [0.2, 5, 4, 5, 2], c: [0.5, 1.0, 1.0, 1.0, 2.0], m: [[0, 'p.G12D', 0, 1]] };
const members = (s: Set<number>) => [...s].sort();
const included = (x: { include: (l: number) => boolean }) => [0, 1, 2, 3, 4].filter(x.include);

test('mutation split: lines without mutation calls and flagged lines are left out', () => {
  const m = makeGrouping('mutation', lines, 'KRAS', g);
  expect(members(m.group)).toEqual([0]);
  expect(included(m)).toEqual([0, 1, 4]);
  expect([m.a, m.b]).toEqual(['KRAS-mutant', 'wild-type']);
});

test('expression split: off against medium or high; low lines and missing values are left out', () => {
  const e = makeGrouping('expression', lines, 'KRAS', g);
  expect(members(e.group)).toEqual([0]);
  expect(included(e)).toEqual([0, 1, 2]);  // 3 flagged, 4 is "low"
});

test('copy split: loss against normal; gains are left out', () => {
  const c = makeGrouping('copy', lines, 'KRAS', g);
  expect(members(c.group)).toEqual([0]);   // ratio 2^0.5 - 1 = 0.41 is a loss
  expect(included(c)).toEqual([0, 1, 2]);
});

test('deep-loss split: only near-complete loss against normal; shallow loss is left out', () => {
  const d = { ...g, c: [0.1, 1.0, 1.0, 1.0, 2.0] }; // 0.1 -> ratio 0.07 (deep loss); 0.5 -> 0.41 (shallow loss)
  const deep = makeGrouping('deeploss', lines, 'MTAP', d);
  expect(members(deep.group)).toEqual([0]);
  expect(included(deep)).toEqual([0, 1, 2]);
  expect(included(makeGrouping('deeploss', lines, 'MTAP', g))).toEqual([1, 2]); // shallow loss at 0 is neither group
  expect([deep.a, deep.b]).toEqual(['MTAP-deep loss', 'MTAP-normal copy number']);
});

test('gain split: gained or amplified against normal; losses are left out', () => {
  const c = makeGrouping('gain', lines, 'ERBB2', g);
  expect(members(c.group)).toEqual([4]);   // ratio 2^2 - 1 = 3 is a gain
  expect(included(c)).toEqual([1, 2, 4]);  // 0 is a loss, 3 is flagged
  expect([c.a, c.b]).toEqual(['ERBB2-gained', 'ERBB2-normal copy number']);
});

test('whole-genome doubling and tissue splits', () => {
  const w = makeGrouping('wgd', lines, '', undefined);
  expect(members(w.group)).toEqual([0]);
  expect(included(w)).toEqual([0, 1, 4]);  // unknown (2) and flagged (3) are out
  const t = makeGrouping('tissue', lines, '', undefined, 'Lung');
  expect(members(t.group)).toEqual([0, 1]);
  expect(included(t)).toEqual([0, 1, 2]);  // no tissue (4) and flagged (3) are out
  expect(t.a).toBe('Lung');
});

test('loss-of-function and hotspot splits: own class against lines with no mutation; the other class is left out', () => {
  // line 0 hotspot only, line 1 loss of function only, line 4 both classes; 2 has no mutation calls, 3 is flagged
  const ctx: GeneContext = { e: [], c: [], m: [[0, 'p.G12D', 0, 1], [1, 'p.R175*', 1, 0], [4, 'p.G12D', 0, 1], [4, 'p.Q5*', 1, 0]] };
  const gof = makeGrouping('mutgof', lines, 'KRAS', ctx);
  expect(members(gof.group)).toEqual([0]);
  expect(included(gof)).toEqual([0]);                 // 1 is loss of function, 4 has both: neither is wild-type
  expect([gof.a, gof.b]).toEqual(['KRAS hotspot mutation', 'wild-type']);
  const lof = makeGrouping('mutlof', lines, 'KRAS', ctx);
  expect(members(lof.group)).toEqual([1]);
  expect(included(lof)).toEqual([1]);
  const none = makeGrouping('mutlof', lines, 'KRAS', { e: [], c: [], m: [[1, 'p.R175*', 1, 0]] });
  expect(included(none)).toEqual([0, 1, 4]);           // wild-type: lines 0 and 4 (2 has no calls, 3 is flagged)
});
