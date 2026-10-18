import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// /associations with a small fake result in place of the R2 bucket (F23).
const index = { release: '24Q4', min_lines: 5, fdr: 0.05, genes: ['EGFR', 'KRAS', 'MYC', 'TP53'], questions: [
  { id: 'tissue:Lung', label: 'Lung vs all other tissues', a: 'Lung', b: 'all other tissues', file: 'f/000.json', lines_a: 40, lines_b: 300, tested: 4, significant: 3 },
  { id: 'mut:KRAS', label: 'KRAS-mutant vs wild-type lines', a: 'KRAS-mutant', b: 'wild-type', file: 'f/001.json', lines_a: 60, lines_b: 280, tested: 4, significant: 1 }] };
const kras = { g: [0, 1, 2, 3], d: [-0.1, -0.9, 0.05, 0.4], p: [0.3, 1e-9, 0.7, 1e-4], q: [0.5, 1e-7, 0.8, 0.01], na: [60, 60, 60, 58], nb: [280, 280, 280, 275] };
const lung = { ...kras, d: [-0.6, -0.1, 0.3, 0.5] };

async function fakeAssoc(page: Page) {
  await page.route('**/associations/**', (route) => {
    const u = route.request().url();
    const body = u.endsWith('index.json') ? index : u.endsWith('000.json') ? lung : u.endsWith('001.json') ? kras : null;
    return body ? route.fulfill({ json: body }) : route.fulfill({ status: 404 });
  });
}
const plot = (page: Page) => page.evaluate(() => {
  const d = (document.getElementById('volcano') as any)?.data ?? [];
  return Object.fromEntries(d.map((t: any) => [t.name, t.x.length]));
});

test('/associations: KRAS question, called genes in the table, the volcano holds every tested gene', async ({ page }) => {
  await fakeAssoc(page);
  await page.goto('/associations');
  await expect(page.getByRole('heading', { name: 'KRAS-mutant vs wild-type lines' })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(2); // KRAS (more) and TP53 (less); EGFR and MYC are not called
  await expect(page.locator('tbody tr').first()).toContainText('KRAS');
  await expect(page.locator('tbody tr').first()).toContainText('more essential in KRAS-mutant');
  await expect.poll(() => plot(page).then((p) => Object.values(p).reduce((a: number, b: any) => a + b, 0))).toBe(4);
  await expect(page.getByRole('heading', { name: 'How these numbers were made' })).toBeVisible();
});

test('/associations: question, thresholds and direction change what is called', async ({ page }) => {
  await fakeAssoc(page);
  await page.goto('/associations');
  await page.getByLabel('Compare cell lines by').selectOption('tissue:Lung');
  await expect(page.getByRole('heading', { name: 'Lung vs all other tissues' })).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(1); // only TP53 passes q <= 0.05 and effect >= 0.2
  await page.getByLabel('Effect at least').selectOption('0');
  await expect(page.locator('tbody tr')).toHaveCount(2); // KRAS joins (q 1e-7, effect -0.1)
  await page.getByLabel('Direction').selectOption('less');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody tr').first()).toContainText('TP53');
});

test('/associations: find a gene reports its numbers and rejects unknown symbols', async ({ page }) => {
  await fakeAssoc(page);
  await page.goto('/associations');
  await page.getByLabel('Gene symbol').fill('kras');
  await page.getByLabel('Gene symbol').press('Escape');
  await page.getByLabel('Gene symbol').dispatchEvent('change');
  await expect(page.locator('#hl-note')).toContainText('KRAS: effect -0.90');
  await page.getByLabel('Gene symbol').fill('ZZZ9');
  await page.getByLabel('Gene symbol').dispatchEvent('change');
  await expect(page.locator('#hl-note')).toContainText('not among the genes tested');
  await expect.poll(() => plot(page).then((p) => Object.keys(p).length)).toBe(3); // no highlight trace for an unknown gene
});

test('/associations: says so when the results are not published, and the page is accessible', async ({ page }) => {
  await page.route('**/associations/**', (route) => route.fulfill({ status: 404 }));
  await page.goto('/associations');
  await expect(page.getByText('Not published yet')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'How these numbers were made' })).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});

test('/associations: the page with data is accessible', async ({ page }) => {
  await fakeAssoc(page);
  await page.goto('/associations');
  await expect(page.locator('tbody tr').first()).toBeVisible();
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});
