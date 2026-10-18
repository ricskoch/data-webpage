import { test, expect } from '@playwright/test';
import { kindCounts, drugCoverage, KIND_TEXT } from '../src/scripts/coverage';

// Data overview (F20): what kinds of treatment exist, and which drugs were screened in which cell lines.
const s = (screen_id: string, treatment: string | null, treatment_category: string | null, cell_line_label: string, rows: number | null, study_id = 'st1') =>
  ({ screen_id, treatment, treatment_category, cell_line_label, rows, study_id });

test('kindCounts counts screens per kind, untreated first, missing kinds as unclassified', () => {
  const c = kindCounts([s('1', null, 'untreated', 'A', 1), s('2', 'X', 'drug_compound', 'A', 1), s('3', 'Y', 'drug_compound', 'B', 1), s('4', 'Z', null, 'B', 1)]);
  expect(c).toEqual({ 'No treatment': 1, 'Drug or compound': 2, 'Not yet sorted': 1 });
});

test('KIND_TEXT has plain-language names for every category in treatment_classes.yaml', () => {
  expect(Object.keys(KIND_TEXT).sort()).toEqual(['biological_agent', 'condition_change', 'culture_format', 'drug_compound', 'genetic_background', 'unclassified', 'untreated']);
});

test('drugCoverage keeps drug_compound screens only, counts screens, studies and the largest gene count per drug and cell line', () => {
  const cov = drugCoverage([
    s('1', 'Olaparib', 'drug_compound', 'HeLa', 100, 'a'), s('2', 'Olaparib', 'drug_compound', 'HeLa', 300, 'b'),
    s('3', 'Olaparib', 'drug_compound', 'K562', 50, 'a'), s('4', 'Hypoxia', 'condition_change', 'HeLa', 999),
    s('5', 'Cisplatin', 'drug_compound', 'HeLa', null, 'a'),
  ]);
  expect(cov.drugs).toEqual([{ drug: 'Olaparib', screens: 3, lines: 2 }, { drug: 'Cisplatin', screens: 1, lines: 1 }]);
  expect(cov.lines).toEqual([{ line: 'HeLa', screens: 3, drugs: 2 }, { line: 'K562', screens: 1, drugs: 1 }]);
  expect(cov.cells.get('Olaparib|HeLa')).toEqual({ screens: 2, studies: 2, genes: 300 });
  expect(cov.cells.get('Cisplatin|HeLa')).toEqual({ screens: 1, studies: 1, genes: 0 });
  expect(cov.cells.has('Hypoxia|HeLa')).toBe(false);
});
