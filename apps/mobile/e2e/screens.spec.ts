/**
 * One screenshot per screen, in screenshots/<name>.png, from the web build. API calls are
 * answered by the same fixtures the Jest screen tests use (src/test/fakeApi.ts), which
 * come from the real FastAPI service. Any uncaught page error fails the test.
 *
 * The web build stubs ARKit, Vision and Skia, so camera screens show their "needs an
 * iPhone" state; layout, copy and data are what these images are for.
 */
import { expect, test, type Page } from '@playwright/test';

import { FakeApi, fixture } from '../src/test/fakeApi';

const report = fixture<{ id: string }>('POST', '/v1/fit/reports');
const garments = fixture<{ id: string; is_reference: boolean }[]>('GET', '/v1/closet/garments');
const reference = garments.find((g) => g.is_reference)!;

async function open(page: Page, path: string, opts: { signedIn?: boolean; api?: (api: FakeApi) => void } = {}) {
  const api = new FakeApi();
  opts.api?.(api);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.route(
    (url) => url.pathname.startsWith('/v1/'),
    async (route) => {
      const req = route.request();
      const body = req.postData();
      const res = api.handle({
        method: req.method(),
        path: new URL(req.url()).pathname,
        headers: req.headers(),
        body: body ? JSON.parse(body) : undefined,
      });
      await route.fulfill({
        status: res.status,
        contentType: 'application/json',
        headers: { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*' },
        body: JSON.stringify(res.body),
      });
    },
  );
  if (opts.signedIn !== false) {
    await page.addInitScript(() => window.localStorage.setItem('styleid.dev_user', 'demo'));
  }
  await page.goto(path);
  await page.waitForLoadState('networkidle');
  return { api, errors };
}

async function shoot(page: Page, name: string, errors: string[]) {
  await page.waitForTimeout(400); // let navigation transitions settle
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  expect(errors, `page errors on ${name}`).toEqual([]);
}

const screens: { name: string; path: string; expectText: RegExp; signedIn?: boolean; api?: (api: FakeApi) => void }[] = [
  { name: '01-sign-in', path: '/', signedIn: false, expectText: /Will this exact top fit you/ },
  { name: '02-closet', path: '/closet', expectText: /Grey everyday tee/ },
  {
    name: '03-closet-empty',
    path: '/closet',
    expectText: /Measure one tee you love/,
    api: (api) => api.set('GET', '/v1/closet/garments', { status: 200, body: [] }),
  },
  { name: '04-garment', path: `/closet/${reference.id}`, expectText: /Measurements \(flat, cm\)/ },
  { name: '05-add-garment', path: '/closet/new', expectText: /How do you want to add it/ },
  { name: '07-capture', path: '/closet/capture', expectText: /Needs an iPhone build/ },
  { name: '08-check', path: '/check', expectText: /Check a product/ },
  { name: '09-fit-report', path: `/check/${report.id}`, expectText: /Our pick/ },
  { name: '10-fit-map', path: `/avatar/${report.id}`, expectText: /Show reference outline/ },
  { name: '11-outcome', path: `/outcomes/${report.id}`, expectText: /How did it go/ },
  { name: '12-body', path: '/body', expectText: /Your body record/ },
  { name: '13-body-manual', path: '/body/manual', expectText: /Tape measurements/ },
  { name: '14-body-scan', path: '/body/scan', expectText: /Needs an iPhone Pro build/ },
];

for (const s of screens) {
  test(s.name, async ({ page }) => {
    const { errors } = await open(page, s.path, s);
    await expect(page.getByText(s.expectText).first()).toBeVisible();
    await shoot(page, s.name, errors);
  });
}

test('06-manual-entry', async ({ page }) => {
  const { errors } = await open(page, '/closet/new');
  await page.getByText('Type measurements').click();
  await page.getByLabel('Name').fill('White oxford tee');
  await page.getByLabel('Chest width, cm').fill('51.5');
  await page.getByLabel('Length, cm', { exact: true }).fill('70');
  await shoot(page, '06-manual-entry', errors);
});
