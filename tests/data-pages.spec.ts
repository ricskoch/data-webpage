import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// /data and /gene with a small fake dataset in place of the R2 bucket (F4, F20, F21).
const screen = (i: number, cell: string, status: string) => ({
  screen_id: `s${i}`, study_id: `st${i % 3}`, author_label: `Author ${i % 3} (2020)`, year: 2015 + (i % 5),
  cell_line_label: cell, library_name: i % 2 ? 'Brunello' : 'TKOv3', perturbation_type: 'knockout',
  selection_type: 'negative_selection', phenotype: 'cell proliferation', experimental_setup: 'timecourse',
  scoring_method: 'Log2FC', result_scope: 'all_genes', normalization_status: status, direction: null,
  direction_evidence: null, known_biology_pass: null, rows: 18000 + i, hits: 10,
  treatment: i % 10 ? null : 'Olaparib', treatment_dose: i % 10 ? null : '5.0 µM', treatment_duration: null,
});
const screens = Array.from({ length: 60 }, (_, i) => screen(i, i < 40 ? 'HeLa' : 'K562', i % 4 ? 'anchored' : 'rank_only'));
const summary = { screens: 60, studies: 3, rows: 1_000_000, by_status: { anchored: 45, rank_only: 15 },
  by_perturbation: { knockout: 60 }, by_selection: { negative_selection: 60 }, top_cell_lines: { HeLa: 40, K562: 20 } };
const geneRows = screens.map((_, i) => [i, i / 59, -i / 59, -i / 10, i % 7 ? 0 : 1, -i / 20]);

async function fakeData(page: Page) {
  await page.route('**/site/**', (route) => {
    const u = route.request().url();
    const body = u.endsWith('summary.json') ? summary : u.endsWith('screens.json') ? screens
      : u.endsWith('genes.json') ? { TP53: ['g1', 0] } : u.endsWith('/g/0000.json') ? { g1: geneRows } : null;
    return body ? route.fulfill({ json: body }) : route.fulfill({ status: 404 });
  });
}

test('/data: filters, sorting and paging on the screens table', async ({ page }) => {
  await fakeData(page);
  await page.goto('/data');
  const count = page.locator('#screens [data-count]');
  await expect(count).toHaveText('60 of 60 screens match.');
  await expect(page.locator('#screens tbody tr')).toHaveCount(25);
  await page.getByLabel('Cell line', { exact: true }).selectOption('K562');
  await expect(count).toHaveText('20 of 60 screens match.');
  await page.getByLabel('Comparable as', { exact: true }).selectOption('rank_only');
  await expect(count).toHaveText('5 of 60 screens match.');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByLabel('Treatment', { exact: true }).selectOption('Olaparib');
  await expect(count).toHaveText('6 of 60 screens match.');
  await expect(page.locator('#screens tbody tr').first().locator('td').nth(7)).toHaveText('Olaparib (5.0 µM)');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await expect(count).toHaveText('60 of 60 screens match.');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.locator('#screens [data-pos]')).toHaveText('Page 2 of 3');
  await page.getByRole('button', { name: 'Genes', exact: true }).click();
  await page.getByRole('button', { name: 'Genes', exact: true }).click();
  await expect(page.locator('#screens tbody tr').first().locator('td').nth(8)).toHaveText('18,059');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

test('/gene: results start most depleted first and can be filtered to hits', async ({ page }) => {
  await fakeData(page);
  await page.goto('/gene?g=tp53');
  await expect(page.locator('#results [data-count]')).toHaveText('60 of 60 screen results match.');
  await expect(page.locator('#results tbody tr').first().locator('td').nth(5)).toHaveText('0.00');
  await page.getByLabel('Treatment', { exact: true }).selectOption('Olaparib');
  await expect(page.locator('#results [data-count]')).toHaveText('6 of 60 screen results match.');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByLabel('Hit', { exact: true }).selectOption('yes');
  await expect(page.locator('#results [data-count]')).toHaveText('9 of 60 screen results match.');
  await page.getByText('How to read the scores').click();
  await expect(page.getByText('A two-point calibration')).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

// Cell line context (M3b) on top of the same fake data; registered after fakeData so it takes precedence for /ctx/.
const ctxLines = {
  release: 'DepMap 24Q4 Public', screen_line: Object.fromEntries(screens.map((s, i) => [s.screen_id, i < 40 ? 0 : 1])),
  lines: [
    { cellosaurus_id: 'CVCL_0030', name: 'HeLa', depmap_id: 'ACH-001086', screens: 40, problematic: false, lineage: 'Cervix', drivers: [] },
    { cellosaurus_id: 'CVCL_0004', name: 'K-562', depmap_id: 'ACH-000551', screens: 20, problematic: false, lineage: 'Myeloid', drivers: ['TP53 p.Q136fs'] },
  ],
};
async function fakeContext(page: Page) {
  await page.route('**/ctx/**', (route) => {
    const u = route.request().url();
    const body = u.endsWith('lines.json') ? ctxLines
      : u.endsWith('/g/0000.json') ? { g1: { e: [6.5, 0.4], c: [1.0, 0.1], m: [[1, 'p.Q136fs', 1, 0]] } } : null;
    return body ? route.fulfill({ json: body }) : route.fulfill({ status: 404 });
  });
}

test('/data: tissue filter and key mutations from the cell line context', async ({ page }) => {
  await fakeData(page);
  await fakeContext(page);
  await page.goto('/data');
  const count = page.locator('#screens [data-count]');
  await page.getByLabel('Tissue', { exact: true }).selectOption('Myeloid');
  await expect(count).toHaveText('20 of 60 screens match.');
  await expect(page.locator('#screens tbody tr').first().locator('td').nth(11)).toHaveText('TP53 p.Q136fs');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByLabel('Search study, cell line, phenotype, treatment or mutated gene').fill('TP53');
  await expect(count).toHaveText('20 of 60 screens match.');
  await expect(page.getByText('both CC BY 4.0')).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

test('/gene: the gene\'s own mutation, expression and copy number in each screened line', async ({ page }) => {
  await fakeData(page);
  await fakeContext(page);
  await page.goto('/gene?g=tp53');
  await expect(page.getByText('of 2 profiled lines carry a protein-altering mutation')).toBeVisible();
  await page.getByLabel('TP53 mutated in line', { exact: true }).selectOption('yes');
  await expect(page.locator('#results [data-count]')).toHaveText('20 of 60 screen results match.');
  const row = page.locator('#results tbody tr').first(); // context columns are the last four
  await expect(row.locator('td').nth(-4)).toHaveText('Myeloid');
  await expect(row.locator('td').nth(-3)).toHaveText('p.Q136fs (loss of function)');
  await expect(row.locator('td').nth(-2)).toHaveText('0.4 off');
  await expect(row.locator('td').nth(-1)).toHaveText('0.10 deep loss');
  await page.getByLabel('Compare lines with and without a mutation in').fill('tp53');
  await page.getByLabel('Compare lines with and without a mutation in').press('Escape'); // dismiss the gene dropdown, which would cover the button
  await page.getByRole('button', { name: 'Compare' }).click();
  await expect(page.locator('#recipe-out')).toContainText('Not enough lines to compare');
  await expect(page.locator('#recipe-out')).toContainText('TP53-mutant lines: 1; TP53-wild-type lines: 1');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

// Desktop workspace (interactive layout): gene dropdown and validation, row selection linked to the plot.
test('/gene: dropdown suggests known genes and unknown symbols are rejected', async ({ page }) => {
  await fakeData(page);
  await page.goto('/gene');
  await expect(async () => {
    await page.getByLabel('Gene symbol').fill('tp');
    await expect(page.getByRole('option', { name: 'TP53' })).toBeVisible({ timeout: 500 });
  }).toPass();
  await page.getByRole('option', { name: 'TP53' }).click();
  await expect(page.locator('#results [data-count]')).toHaveText('60 of 60 screen results match.');
  await page.getByLabel('Gene symbol').fill('ZZZ9');
  await page.getByLabel('Gene symbol').press('Escape');
  await page.getByRole('button', { name: 'Look up' }).click();
  await expect(page.locator('#form-error')).toContainText('not a gene in this collection');
});

test('/gene: selecting a row shows its details and marks its dot in the plot; the plot follows the filters', async ({ page }) => {
  await fakeData(page);
  await page.goto('/gene?g=TP53');
  await expect(page.locator('#strip circle')).toHaveCount(60);
  await page.locator('#results tbody tr').nth(2).click();
  await expect(page.locator('[data-detail] h3')).toHaveText('Author 2 (2020)');
  await expect(page.locator('#strip circle.picked')).toHaveCount(1);
  await page.getByLabel('Treatment', { exact: true }).selectOption('Olaparib');
  await expect(page.locator('#strip circle')).toHaveCount(6);
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.locator('#strip circle').nth(10).dispatchEvent('click');
  await expect(page.locator('#strip circle.picked')).toHaveCount(1);
  await expect(page.locator('#results tr[aria-current="true"]')).toHaveCount(1);
});

test('/data: arrow keys move the selection and the detail panel follows', async ({ page }) => {
  await fakeData(page);
  await page.goto('/data');
  await page.locator('#screens tbody tr').first().focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-detail] h3')).toHaveText('Author 0 (2020)');
  await page.keyboard.press('ArrowDown');
  await expect(page.locator('[data-detail] h3')).toHaveText('Author 1 (2020)');
  await page.keyboard.press('/');
  await expect(page.locator('#screens [data-search]')).toBeFocused();
});

// Reactome pathway picker (optional data): limits the gene dropdown and links genes to pathways.
test('/gene: pathway picker limits the gene dropdown and offers its genes', async ({ page }) => {
  await fakeData(page);
  await page.route('**/pathways/**', (route) => route.fulfill({ json: { release: '95', pathways: [
    { id: 'R-HSA-1', name: 'Apoptosis', genes: ['TP53', 'BAX'] },
    { id: 'R-HSA-2', name: 'Cell cycle', genes: ['TP53', 'CDK1'] },
  ] } }));
  await page.goto('/gene');
  await expect(page.getByRole('heading', { name: 'Browse by pathway' })).toBeVisible();
  await page.getByLabel('Pathway', { exact: true }).fill('apop');
  await page.getByRole('option', { name: 'Apoptosis' }).click();
  await expect(page.locator('#pw-out')).toContainText('1 of 2 genes of this pathway are in the screens');
  await page.locator('#pw-out').getByRole('button', { name: 'TP53' }).click();
  await expect(page.locator('#results [data-count]')).toHaveText('60 of 60 screen results match.');
  await expect(page.getByRole('button', { name: 'Cell cycle' })).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});
