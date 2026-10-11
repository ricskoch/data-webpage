import { test, expect } from '@playwright/test';
import { geneInLine, copyLabel, expressionLabel, type GeneContext } from '../src/scripts/context';

// Pure-logic tests for the cell line context helpers (M3b).
const g: GeneContext = { e: [5.2, null, 0.3], c: [1.0, 2.6, 0.1], m: [[1, 'p.R175H', 0, 1], [2, 'p.Q136*', 1, 0], [2, 'p.E2K', 0, 0]] };

test('geneInLine: values for one line, mutations joined with their flags', () => {
  expect(geneInLine(g, 0)).toEqual({ expression: 5.2, copyNumber: 1.0, mutation: null });
  expect(geneInLine(g, 1)).toEqual({ expression: null, copyNumber: 2.6, mutation: 'p.R175H (hotspot)' });
  expect(geneInLine(g, 2).mutation).toBe('p.Q136* (loss of function), p.E2K');
  expect(geneInLine(undefined, 0)).toEqual({ expression: null, copyNumber: null, mutation: null });
});

test('copyLabel: log2(ratio + 1) bands, 1 = normal', () => {
  expect(copyLabel(1.0)).toBe('normal');       // ratio 1
  expect(copyLabel(0.1)).toBe('deep loss');    // ratio 0.07
  expect(copyLabel(0.6)).toBe('loss');         // ratio 0.52
  expect(copyLabel(1.5)).toBe('gain');         // ratio 1.83
  expect(copyLabel(2.6)).toBe('amplified');    // ratio 5.06
  expect(copyLabel(null)).toBeNull();
});

test('expressionLabel: log2(TPM+1) bands', () => {
  expect(expressionLabel(0.3)).toBe('off');
  expect(expressionLabel(2)).toBe('low');
  expect(expressionLabel(5)).toBe('medium');
  expect(expressionLabel(8)).toBe('high');
  expect(expressionLabel(null)).toBeNull();
});
