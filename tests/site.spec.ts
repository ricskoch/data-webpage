import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const pages = [
  { path: '/', heading: /Explore human CRISPR screens/ },
  { path: '/about', heading: /About/ },
  { path: '/data-policy', heading: /Data policy/ },
];

for (const p of pages) {
  test.describe(p.path, () => {
    test('renders heading and has no accessibility violations', async ({ page }) => {
      await page.goto(p.path);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(p.heading);
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
      expect(results.violations).toEqual([]);
    });

    test('has no horizontal scroll', async ({ page }) => {
      await page.goto(p.path);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(overflow).toBe(false);
    });

    test('sets no cookies', async ({ page, context }) => {
      await page.goto(p.path);
      expect(await context.cookies()).toEqual([]);
    });
  });
}

test('navigation reaches every page', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'About' }).click();
  await expect(page).toHaveURL(/\/about$/);
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Data policy' }).click();
  await expect(page).toHaveURL(/\/data-policy$/);
});

test('unknown page shows the 404 page', async ({ page }) => {
  const res = await page.goto('/does-not-exist');
  expect(res?.status()).toBe(404);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Page not found');
});
