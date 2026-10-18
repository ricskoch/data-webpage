import { test, expect } from '@playwright/test';
import { suggest, exactSymbol } from '../src/scripts/combobox';

// Pure-logic tests for the gene autocomplete on /gene (F20).
const genes = ['TP53', 'TP63', 'TP73', 'ATP5F1A', 'KRAS', 'NRAS', 'HRAS', 'RASA1', 'BRCA1'];

test('suggest: symbols starting with the query come first, shorter first, then symbols containing it', () => {
  expect(suggest(genes, 'tp')).toEqual(['TP53', 'TP63', 'TP73', 'ATP5F1A']);
  expect(suggest(genes, 'ras')).toEqual(['RASA1', 'HRAS', 'KRAS', 'NRAS']);
});

test('suggest: empty or unmatched query gives nothing; limit is respected', () => {
  expect(suggest(genes, '  ')).toEqual([]);
  expect(suggest(genes, 'zzz')).toEqual([]);
  expect(suggest(genes, 'a', 3).length).toBe(3);
});

test('exactSymbol: case-insensitive match against the known list, otherwise undefined', () => {
  expect(exactSymbol(genes, ' kras ')).toBe('KRAS');
  expect(exactSymbol(genes, 'KRA')).toBeUndefined();
});
