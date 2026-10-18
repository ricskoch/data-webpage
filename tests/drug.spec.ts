import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { joinVectors, topDifferences, drugsOf, drugSummary } from '../src/scripts/drug';

// Drug page (F22): pure joining logic, then the page with fake data in place of the R2 bucket.
test('joinVectors keeps only genes in both screens, x = no-drug, y = drug', () => {
  const pts = joinVectors({ i: [1, 2, 3], z: [0, 1, 2] }, { i: [3, 2, 9], z: [5, 4, 3] });
  expect(pts).toEqual([[2, 5, 3], [1, 4, 2]]);
});

test('topDifferences ranks by drug minus no-drug, ties by gene index', () => {
  const pts: [number, number, number][] = [[0, 0, 5], [0, 3, 4], [0, -3, 2], [0, -3, 1]];
  expect(topDifferences(pts, 1, 1)).toEqual([[0, 3, 4]]);
  expect(topDifferences(pts, -1, 2).map((p) => p[2])).toEqual([1, 2]);
});

test('drugsOf lists drugs that have a published vector, sorted', () => {
  expect(drugsOf([{ treatment: 'b', has_z: true }, { treatment: 'A', has_z: true }, { treatment: 'c', has_z: false }, { treatment: null, has_z: true }])).toEqual(['A', 'b']);
});

test('drugSummary counts screens, lines and hits per treatment, hits first', () => {
  const r = (treatment: string | null, cell_line_label: string, hit: number) => ({ treatment, cell_line_label, hit });
  expect(drugSummary([r('B', 'HeLa', 0), r('A', 'HeLa', 1), r('A', 'K562', 1), r(null, 'HeLa', 1), r('B', 'HeLa', 0)]))
    .toEqual([{ drug: 'A', screens: 2, hits: 2, lines: 2 }, { drug: 'B', screens: 2, hits: 0, lines: 1 }]);
});

const base = { study_id: 'st', author_label: 'Au (2020)', year: 2020, cell_line_label: 'HAP1', library_name: 'TKOv3', perturbation_type: 'knockout',
  selection_type: 'negative_selection', phenotype: 'x', scoring_method: 'DrugZ', result_scope: 'all_genes', normalization_status: 'rank_only',
  direction: null, direction_evidence: null, known_biology_pass: null, rows: 10, hits: 1, has_z: true, primary_score_name: 'DrugZ', primary_score_position: 1 };
const screens = [
  { ...base, screen_id: '1', experimental_setup: 'Drug Exposure', treatment: 'Olaparib', treatment_dose: '1 µM', treatment_duration: null },
  { ...base, screen_id: '2', experimental_setup: 'timecourse', treatment: null, treatment_dose: null, treatment_duration: null, primary_score_name: 'Log2FC' },
];
const perts = ['TP53', 'BRCA2', 'ACTB', 'MYC'];
const vectors: Record<string, unknown> = {
  '0001': { i: [0, 1, 2, 3], z: [0, -4, 1, 0.5] }, '0002': { i: [0, 1, 2], z: [0, 0, 1] },
};

async function fakeData(page: Page) {
  await page.route('**/site/**', (route) => {
    const u = new URL(route.request().url()).pathname;
    const m = u.match(/\/s\/(\d{4})\.json$/);
    const body = u.endsWith('screens.json') ? screens : u.endsWith('drug_pairs.json') ? { '1': [['2', 'same_cell_line']] }
      : u.endsWith('perts.json') ? perts : m ? vectors[m[1]] : null;
    return body ? route.fulfill({ json: body }) : route.fulfill({ status: 404 });
  });
}

test('/drug: pick a drug, see the match level, highlight a gene, read the top differences', async ({ page }) => {
  await fakeData(page);
  await page.goto('/drug');
  await expect(page.getByLabel('Drug', { exact: true })).toHaveValue('Olaparib');
  await expect(page.locator('#match')).toContainText('Other study, same cell line');
  await expect(page.locator('#stats')).toContainText('3 genes in both screens');
  await expect(page.locator('#tops tbody').first().locator('tr').first()).toContainText('BRCA2');
  await page.getByLabel('Highlight gene').fill('brca2');
  await expect(page.locator('#stats')).toHaveAttribute('data-found', '1');
  await page.getByLabel('Highlight gene').fill('MYC');
  await expect(page.locator('#stats')).toHaveAttribute('data-found', '0');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

// The scatter is a Plotly chart: its traces tell how many genes are coloured and which gene is ringed.
const traces = (page: Page) => page.evaluate(() => Object.fromEntries(((document.getElementById('plot') as any)?.data ?? []).map((t: any) => [t.name, t.x.length])));

test('/drug: genes whose drug score differs by the chosen gap are coloured; a click on a dot highlights its gene', async ({ page }) => {
  await fakeData(page);
  await page.goto('/drug');
  await expect.poll(() => traces(page)).toEqual({ 'within the gap': 2, 'lower with drug (by 3 or more)': 1, 'higher with drug (by 3 or more)': 0 });
  await page.getByLabel('Colour genes whose drug score differs by at least').selectOption('0');
  await expect.poll(() => traces(page)).toEqual({ genes: 3 });
  await page.evaluate(() => (document.getElementById('plot') as any).emit('plotly_click', { points: [{ customdata: 'BRCA2' }] }));
  await expect(page.getByLabel('Highlight gene')).toHaveValue('BRCA2');
  await expect.poll(() => traces(page)).toEqual({ genes: 3, BRCA2: 1 });
});
