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

test('versioned adds the build id to a data URL so a new deploy skips cached copies', async () => {
  const { versioned } = await import('../src/scripts/version');
  expect(versioned('https://x.test/a.json')).toBe('https://x.test/a.json?v=dev');
  expect(versioned('https://x.test/a.json?q=1')).toBe('https://x.test/a.json?q=1&v=dev');
});

test('applyDisplayNames shows display names, keeps the source labels, and falls back when a name is missing', async () => {
  const { applyDisplayNames } = await import('../src/scripts/data');
  const base = { screen_id: '1', study_id: 's' } as any;
  const [a, b, c] = applyDisplayNames([
    { ...base, cell_line_label: 'MDA-MB-231', cell_line_display: 'MDAMB231', treatment: 'olaparib', treatment_display: 'Olaparib' },
    { ...base, cell_line_label: 'HeLa', treatment: null },
    { ...base, cell_line_label: 'K562', treatment: 'DMSO', treatment_display: null },
  ]);
  expect([a.cell_line_label, a.treatment, a.cell_line_raw, a.treatment_raw]).toEqual(['MDAMB231', 'Olaparib', 'MDA-MB-231', 'olaparib']);
  expect([b.cell_line_label, b.treatment]).toEqual(['HeLa', null]);
  expect([c.cell_line_label, c.treatment]).toEqual(['K562', 'DMSO']);
  expect(applyDisplayNames([a])[0].treatment).toBe('Olaparib'); // second call changes nothing
});
