import { test, expect } from '@playwright/test';
import { median, mannWhitney, bootstrapDiff, dependencyByMutation, verdict, MIN_LINES } from '../src/scripts/recipe';

// Pure-logic tests for recipe 2 ("dependency by mutation"). The independent SciPy comparison lives in
// tests/reference/test_recipe_reference.py; these pin the hand-checkable cases.
test('median: odd, even, empty', () => {
  expect(median([3, 1, 2])).toBe(2);
  expect(median([4, 1, 3, 2])).toBe(2.5);
  expect(median([])).toBeNaN();
});

test('mannWhitney: complete separation of 3 vs 3 (U = 0, p = 0.0809 by hand)', () => {
  const { u, p } = mannWhitney([1, 2, 3], [4, 5, 6]);
  expect(u).toBe(0);
  // s = sqrt(9/12 * 7) = 2.2913, z = (9 - 4.5 - 0.5) / s = 1.7457, p = 2 * (1 - Phi(z))
  expect(p).toBeCloseTo(0.0809, 4);
  expect(mannWhitney([4, 5, 6], [1, 2, 3]).u).toBe(9);
  expect(mannWhitney([1, 1], [1, 1]).p).toBeNaN();
});

test('mannWhitney: ties get average ranks', () => {
  // a = [1, 2, 2], b = [3, 2]: sorted 1, 2, 2, 2, 3 get ranks 1, 3, 3, 3, 5; rank sum of a = 7, U = 7 - 6
  expect(mannWhitney([1, 2, 2], [3, 2]).u).toBe(1 + 3 + 3 - 6);
});

test('bootstrapDiff: deterministic and brackets the observed difference', () => {
  const a = [-1.1, -0.9, -1.0, -0.8, -1.2, -0.95], b = [0.1, -0.1, 0.05, 0, -0.05, 0.2];
  const ci = bootstrapDiff(a, b);
  expect(bootstrapDiff(a, b)).toEqual(ci);
  expect(ci[0]).toBeLessThan(median(a) - median(b));
  expect(ci[1]).toBeGreaterThan(median(a) - median(b));
  expect(ci[1]).toBeLessThan(0);
});

test('dependencyByMutation: one value per line, excluded lines dropped, minimum group size', () => {
  const perScreen = [
    { line: 0, value: -1 }, { line: 0, value: -0.6 }, { line: 0, value: -0.2 }, // line 0: three screens, median -0.6
    ...[1, 2, 3, 4].map((line) => ({ line, value: -0.8 })),
    ...[5, 6, 7, 8, 9].map((line) => ({ line, value: 0 })),
    { line: 10, value: -3 }, // excluded (e.g. flagged line)
  ];
  const c = dependencyByMutation(perScreen, new Set([0, 1, 2, 3, 4, 10]), (l) => l !== 10);
  expect(c.mutant.find((v) => v.line === 0)).toEqual({ line: 0, value: -0.6, screens: 3 });
  expect([c.mutant.length, c.wildtype.length]).toEqual([5, 5]);
  expect(c.testable).toBe(true);
  expect(c.diff).toBeCloseTo(-0.8, 10);
  expect(verdict(c, 'X', 'Y')).toBe('Knocking out X hurts Y-mutant lines more (or helps them less) than wild-type lines.');
  const small = dependencyByMutation(perScreen, new Set([0]), () => true);
  expect(small.testable).toBe(false);
  expect(verdict(small, 'X', 'Y')).toContain(`at least ${MIN_LINES}`);
});
