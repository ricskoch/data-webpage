import { test, expect } from '@playwright/test';
import { filterRows, sortRows, pageOf, facetCounts } from '../src/scripts/table';

// Pure-logic tests for the paged, filterable tables on /data and /gene (F4, F20, F21).
type R = { cell: string | null; study: string; score: number | null };
const rows: R[] = [
  { cell: 'HeLa', study: 'Hart 2015', score: -1.2 },
  { cell: 'K562', study: 'Wang 2015', score: 0.3 },
  { cell: 'HeLa', study: 'Wang 2015', score: null },
  { cell: null, study: 'Behan 2019', score: -0.1 },
  { cell: 'A375', study: 'Behan 2019', score: -0.1 },
];
const facets = { cell: (r: R) => r.cell, study: (r: R) => r.study };

test('filterRows: exact facet match, combined with AND', () => {
  expect(filterRows(rows, facets, { cell: 'HeLa' }, '', []).length).toBe(2);
  expect(filterRows(rows, facets, { cell: 'HeLa', study: 'Wang 2015' }, '', [])).toEqual([rows[2]]);
  expect(filterRows(rows, facets, { cell: '' }, '', []).length).toBe(5);
});

test('filterRows: missing values are matched by the "unknown" option', () => {
  expect(filterRows(rows, facets, { cell: 'unknown' }, '', [])).toEqual([rows[3]]);
});

test('filterRows: free text is case-insensitive over the given fields', () => {
  expect(filterRows(rows, facets, {}, 'behan', [(r) => r.study]).length).toBe(2);
  expect(filterRows(rows, facets, {}, '  k56 ', [(r) => r.cell, (r) => r.study])).toEqual([rows[1]]);
});

test('sortRows: numbers ascending/descending, missing values always last, stable, no mutation', () => {
  const copy = [...rows];
  const asc = sortRows(rows, (r) => r.score, 'asc');
  expect(asc.map((r) => r.score)).toEqual([-1.2, -0.1, -0.1, 0.3, null]);
  expect(asc[1]).toBe(rows[3]); // stable: original order kept for ties
  expect(sortRows(rows, (r) => r.score, 'desc').map((r) => r.score)).toEqual([0.3, -0.1, -0.1, -1.2, null]);
  expect(rows).toEqual(copy);
});

test('sortRows: text sorts alphabetically, ignoring case', () => {
  const out = sortRows([{ s: 'b' }, { s: 'A' }, { s: 'c' }], (r) => r.s, 'asc');
  expect(out.map((r) => r.s)).toEqual(['A', 'b', 'c']);
});

test('pageOf: slices, clamps the page number, reports the page count', () => {
  const n = Array.from({ length: 55 }, (_, i) => i);
  expect(pageOf(n, 1, 25)).toEqual({ rows: n.slice(0, 25), page: 1, pages: 3 });
  expect(pageOf(n, 3, 25).rows).toEqual([50, 51, 52, 53, 54]);
  expect(pageOf(n, 9, 25).page).toBe(3);
  expect(pageOf(n, 0, 25).page).toBe(1);
  expect(pageOf([], 1, 25)).toEqual({ rows: [], page: 1, pages: 1 });
});

test('facetCounts: most common first, then alphabetical, missing as "unknown"', () => {
  expect(facetCounts(rows, facets.cell)).toEqual([['HeLa', 2], ['A375', 1], ['K562', 1], ['unknown', 1]]);
});
