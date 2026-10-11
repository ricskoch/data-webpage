import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// /data and /gene with a small fake dataset in place of the R2 bucket (F4, F20, F21).
const screen = (i: number, cell: string, status: string) => ({
  screen_id: `s${i}`, study_id: `st${i % 3}`, author_label: `Author ${i % 3} (2020)`, year: 2015 + (i % 5),
  cell_line_label: cell, library_name: i % 2 ? 'Brunello' : 'TKOv3', perturbation_type: 'knockout',
  selection_type: 'negative_selection', phenotype: 'cell proliferation', experimental_setup: 'timecourse',
  scoring_method: 'Log2FC', result_scope: 'all_genes', normalization_status: status, direction: null,
  direction_evidence: null, known_biology_pass: null, rows: 18000 + i, hits: 10,
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
  await expect(count).toHaveText('60 of 60 screens match.');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.locator('#screens [data-pos]')).toHaveText('Page 2 of 3');
  await page.getByRole('button', { name: 'Genes', exact: true }).click();
  await page.getByRole('button', { name: 'Genes', exact: true }).click();
  await expect(page.locator('#screens tbody tr').first().locator('td').nth(7)).toHaveText('18,059');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

test('/gene: results start most depleted first and can be filtered to hits', async ({ page }) => {
  await fakeData(page);
  await page.goto('/gene?g=tp53');
  await expect(page.locator('#results [data-count]')).toHaveText('60 of 60 screen results match.');
  await expect(page.locator('#results tbody tr').first().locator('td').nth(4)).toHaveText('0.00');
  await page.getByLabel('Hit', { exact: true }).selectOption('yes');
  await expect(page.locator('#results [data-count]')).toHaveText('9 of 60 screen results match.');
  await page.getByText('How to read the scores').click();
  await expect(page.getByText('A two-point calibration')).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});
