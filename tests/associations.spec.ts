import { test, expect } from '@playwright/test';
import { callOf, topHits, type Result } from '../src/scripts/associations';

// Pure-logic tests for the associations page. d = median(A) - median(B) on the essential scale, so negative = more essential in A.
const genes = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE'];
const r: Result = { g: [0, 1, 2, 3, 4], d: [-0.8, -0.1, 0.6, -0.5, 0.9], p: [1e-8, 0.2, 1e-5, 1e-6, 0.3],
  q: [1e-6, 0.4, 1e-3, 1e-5, 0.5], na: [8, 8, 8, 8, 8], nb: [30, 30, 30, 30, 30] };

test('callOf: needs both a small q and a large enough effect', () => {
  expect(callOf(-0.8, 1e-6, 0.05, 0.2)).toBe('more');
  expect(callOf(0.6, 1e-3, 0.05, 0.2)).toBe('less');
  expect(callOf(-0.1, 1e-6, 0.05, 0.2)).toBe('ns'); // effect too small
  expect(callOf(-0.8, 0.4, 0.05, 0.2)).toBe('ns'); // not significant
  expect(callOf(-0.2, 0.05, 0.05, 0.2)).toBe('more'); // limits are inclusive
});

test('topHits: sorted by q then by size of effect, filtered, limited, with symbols', () => {
  const all = topHits(r, genes, 0.05, 0.2, 10);
  expect(all.map((h) => h.gene)).toEqual(['AAA', 'DDD', 'CCC']);
  expect(topHits(r, genes, 0.05, 0.2, 2).map((h) => h.gene)).toEqual(['AAA', 'DDD']);
  expect(topHits(r, genes, 0.05, 0.7, 10).map((h) => h.gene)).toEqual(['AAA']);
  expect(topHits(r, genes, 0.05, 0, 10, 'more').map((h) => h.gene)).toEqual(['AAA', 'DDD']);
});

test('topHits: equal q ties go to the larger effect, and null q is never a hit', () => {
  const t: Result = { g: [0, 1, 2], d: [-0.3, -0.9, -0.9], p: [0.001, 0.001, null], q: [0.01, 0.01, null], na: [5, 5, 5], nb: [5, 5, 5] };
  expect(topHits(t, ['X', 'Y', 'Z'], 0.05, 0, 10).map((h) => h.gene)).toEqual(['Y', 'X']);
});
