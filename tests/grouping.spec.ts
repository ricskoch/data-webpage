import { test, expect } from '@playwright/test';
import { makeGrouping } from '../src/scripts/grouping';
import type { GeneContext, Lines } from '../src/scripts/context';

// Pure-logic tests for the ways lines are split into two groups (recipe 2, other splits).
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

test('whole-genome doubling and tissue splits', () => {
  const w = makeGrouping('wgd', lines, '', undefined);
  expect(members(w.group)).toEqual([0]);
  expect(included(w)).toEqual([0, 1, 4]);  // unknown (2) and flagged (3) are out
  const t = makeGrouping('tissue', lines, '', undefined, 'Lung');
  expect(members(t.group)).toEqual([0, 1]);
  expect(included(t)).toEqual([0, 1, 2]);  // no tissue (4) and flagged (3) are out
  expect(t.a).toBe('Lung');
});
