import { test, expect } from '@playwright/test';
import { groupForChart } from '../src/scripts/explorer';

// Pure-logic tests for the grouped plot on /gene: which groups get a row, in which order.
const rows = (spec: Record<string, number[]>) => Object.entries(spec).flatMap(([g, ranks]) => ranks.map((rank) => ({ g, rank })));
const by = { label: (r: { g: string | null }) => r.g, value: (r: { rank: number }) => r.rank };

test('groupForChart: groups ordered by median value, most depleted first', () => {
  const out = groupForChart(rows({ B: [0.8, 0.9], A: [0.1, 0.3], C: [0.5] }), by.label, by.value);
  expect(out.map((g) => g.label)).toEqual(['A', 'C', 'B']);
  expect(out[0].items).toHaveLength(2);
});

test('groupForChart: missing labels become "unknown", never dropped', () => {
  const out = groupForChart([{ g: null, rank: 0.2 }, { g: 'A', rank: 0.4 }], by.label, by.value);
  expect(out.map((g) => g.label).sort()).toEqual(['A', 'unknown']);
});

test('groupForChart: beyond max, the rarest groups are pooled into one "other" row that still holds every item', () => {
  const spec: Record<string, number[]> = { A: [0.1, 0.1, 0.1], B: [0.2, 0.2], C: [0.3], D: [0.4], E: [0.5] };
  const input = rows(spec);
  const out = groupForChart(input, by.label, by.value, 3);
  expect(out).toHaveLength(3);
  const other = out.find((g) => g.label === 'other (3 groups)')!;
  expect(other.items).toHaveLength(3);
  expect(out.flatMap((g) => g.items)).toHaveLength(input.length);
});

test('groupForChart: no rows, no groups', () => {
  expect(groupForChart([], by.label, by.value)).toEqual([]);
});
