import { test, expect } from '@playwright/test';
import { bandOf, summarize, overChance, type Pair } from '../src/scripts/repro';

// Data overview (F20): reading the reproducibility numbers of repeated drug screens.
const pair = (drug: string, line: string, rho: number, overlap = 10, expected = 2, same = 0): Pair => [drug, line, 0, 1, 5000, rho, overlap, expected, same];

test('bandOf: 0.5 and above agree, 0.2 up to 0.5 partly, below 0.2 barely', () => {
  expect([0.9, 0.5, 0.49, 0.2, 0.19, -0.3].map(bandOf)).toEqual(['agree', 'agree', 'partly', 'partly', 'weak', 'weak']);
});

test('summarize counts pairs, drug and cell line combinations, bands and the median rho', () => {
  const s = summarize([pair('A', 'HeLa', 0.8), pair('A', 'HeLa', 0.3), pair('A', 'K562', 0.1), pair('B', 'HeLa', -0.2)]);
  expect(s).toMatchObject({ pairs: 4, combos: 3, bands: { agree: 1, partly: 1, weak: 2 } });
  expect(s.median).toBeCloseTo(0.2, 10);
  expect(summarize([])).toEqual({ pairs: 0, combos: 0, median: null, bands: { agree: 0, partly: 0, weak: 0 } });
});

test('overChance divides the shared strongest genes by the number expected by chance', () => {
  expect(overChance(pair('A', 'HeLa', 0.5, 30, 2))).toBe(15);
  expect(overChance(pair('A', 'HeLa', 0.5, 30, 0))).toBe(0);
});
