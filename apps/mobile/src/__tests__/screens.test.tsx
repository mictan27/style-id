/**
 * Screen tests: the real expo-router app rendered under Jest, against a fake API that
 * serves responses exported from the real FastAPI service and fit engine.
 */
import { fireEvent, waitFor } from 'expo-router/testing-library';

import type { FitReport, Garment } from '@/api/schema';
import { zoneDisplayName } from '@/fit/format';
import { fixture } from '@/test/fakeApi';
import { fakeApi, renderApp } from '@/test/renderApp';

jest.setTimeout(30_000);

const report = fixture<FitReport>('POST', '/v1/fit/reports');
const garments = fixture<Garment[]>('GET', '/v1/closet/garments');
const reference = garments.find((g) => g.is_reference)!;

describe('sign-in', () => {
  test('signed-out users land on sign-in and the dev handle signs them in', async () => {
    const { screen } = await renderApp('/closet', { signedIn: false });
    expect(await screen.findByText(/Will this exact top fit you/)).toBeTruthy();

    const continueButton = () => screen.getByRole('button', { name: 'Continue as dev user' });
    expect(continueButton()).toBeDisabled();
    await fireEvent.changeText(screen.getByPlaceholderText('handle, e.g. william'), 'william');
    await fireEvent.press(continueButton());

    expect(await screen.findByText(reference.name!)).toBeTruthy();
    await waitFor(() => expect(fakeApi().callsTo('GET', '/v1/closet/garments')).toHaveLength(1));
    expect(fakeApi().calls[0]!.headers['x-dev-user']).toBe('william');
  });
});

describe('closet', () => {
  test('lists garments with the reference starred and chest width', async () => {
    const { screen } = await renderApp('/closet');
    expect(await screen.findByText('Grey everyday tee')).toBeTruthy();
    expect(screen.getByText('Navy crew knit')).toBeTruthy();
    expect(screen.getAllByLabelText('Reference garment')).toHaveLength(1);
    expect(screen.getByText(/T-shirt · M · chest 52 cm/)).toBeTruthy();
  });

  test('an empty closet explains the reference tee', async () => {
    fakeApi().set('GET', '/v1/closet/garments', { status: 200, body: [] });
    const { screen } = await renderApp('/closet');
    expect(await screen.findByText('Measure one tee you love')).toBeTruthy();
  });

  test('a server error is shown, not swallowed', async () => {
    fakeApi().set('GET', '/v1/closet/garments', { status: 500, body: { detail: 'database is down' } });
    const { screen } = await renderApp('/closet');
    expect(await screen.findByText(/database is down/, {}, { timeout: 5000 })).toBeTruthy();
  });
});

describe('manual garment entry', () => {
  test('sends cm measurements and opens the new garment', async () => {
    const created = { ...reference, id: 'new-garment', name: 'White oxford tee' };
    fakeApi().set('POST', '/v1/closet/garments', { status: 201, body: created });
    fakeApi().set('GET', '/v1/closet/garments/new-garment', { status: 200, body: created });

    const { screen, getPathname } = await renderApp('/closet/new');
    await fireEvent.press(await screen.findByText('Type measurements'));

    const save = () => screen.getByRole('button', { name: 'Save garment' });
    expect(save()).toBeDisabled();

    await fireEvent.changeText(screen.getByLabelText('Name'), 'White oxford tee');
    await fireEvent.changeText(screen.getByLabelText('Size label'), 'm');
    await fireEvent.changeText(screen.getByLabelText('Chest width, cm'), '51,5');
    await fireEvent.changeText(screen.getByLabelText('Length, cm'), '70');
    expect(save()).toBeEnabled();
    await fireEvent.press(save());

    await waitFor(() => expect(getPathname()).toBe('/closet/new-garment'));
    const [call] = fakeApi().callsTo('POST', '/v1/closet/garments');
    expect(call!.body).toMatchObject({
      name: 'White oxford tee',
      kind: 'tee',
      size_label: 'm',
      is_reference: true,
      measurements: {
        chest_width: { value_cm: 51.5, source: 'manual' },
        length: { value_cm: 70, source: 'manual' },
      },
    });
  });

  test('rejects out-of-range values', async () => {
    const { screen } = await renderApp('/closet/new');
    await fireEvent.press(await screen.findByText('Type measurements'));
    await fireEvent.changeText(screen.getByLabelText('Chest width, cm'), '500');
    expect(screen.getByText('Enter a value between 0 and 400 cm')).toBeTruthy();
  });
});

describe('product check', () => {
  test('a pasted link runs the check and opens the fit report', async () => {
    const { screen, getPathname } = await renderApp('/check');
    const button = () => screen.getByRole('button', { name: 'Check fit' });
    expect(await screen.findByRole('button', { name: 'Check fit' })).toBeDisabled();

    await fireEvent.changeText(screen.getByPlaceholderText('https://shop.example.com/tee'), report.product.url_original);
    await fireEvent.press(button());

    await waitFor(() => expect(getPathname()).toBe(`/check/${report.id}`));
    expect(fakeApi().callsTo('POST', '/v1/products/check')[0]!.body).toMatchObject({
      url: report.product.url_original,
      garment_kind: 'tee',
    });
    expect(fakeApi().callsTo('POST', '/v1/fit/reports')[0]!.body).toMatchObject({ product_id: report.product.id });
  });

  test('past reports show the pick and runner-up', async () => {
    const { screen } = await renderApp('/check');
    expect(await screen.findByText('Pick: M · then S')).toBeTruthy();
    expect(screen.getByText('Heavyweight tee')).toBeTruthy();
  });
});

describe('fit report', () => {
  test('shows pick, runner-up, what changes between them and excluded sizes', async () => {
    const { screen } = await renderApp(`/check/${report.id}`);
    expect(await screen.findByText('Our pick')).toBeTruthy();
    expect(screen.getByText('Heavyweight tee')).toBeTruthy();
    expect(screen.queryByText('n/a')).toBeNull();
    expect(screen.getByText('Runner-up')).toBeTruthy();
    expect(screen.getByText('What would change: M → S')).toBeTruthy();
    expect(screen.getByText(/XL: shoulder seam sits 2.5 cm outside your shoulder point/)).toBeTruthy();
    expect(screen.getByText(/compared with your Grey everyday tee/)).toBeTruthy();
    // Every zone of the pick gets a row.
    for (const zone of report.report.pick!.zones) {
      expect(screen.getAllByText(zoneDisplayName(zone.zone)).length).toBeGreaterThan(0);
    }
  });

  test('an unknown report id shows an error', async () => {
    const { screen } = await renderApp('/check/does-not-exist');
    expect(await screen.findByText(/no route|not found/i, {}, { timeout: 5000 })).toBeTruthy();
  });
});

describe('outcome check-in', () => {
  test('a kept purchase posts the size bought', async () => {
    const { screen } = await renderApp(`/outcomes/${report.id}`);
    await fireEvent.press(await screen.findByRole('radio', { name: 'M' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Kept it' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Submit' }));
    await waitFor(() => expect(fakeApi().callsTo('POST', '/v1/outcomes')).toHaveLength(1));
    expect(fakeApi().callsTo('POST', '/v1/outcomes')[0]!.body).toMatchObject({
      fit_report_id: report.id,
      size_bought: 'M',
      kept: true,
      zone: null,
    });
  });

  test('a return needs the problem zone and direction', async () => {
    const { screen } = await renderApp(`/outcomes/${report.id}`);
    await fireEvent.press(await screen.findByRole('radio', { name: 'S' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Returned it' }));
    const submit = () => screen.getByRole('button', { name: 'Submit' });
    expect(submit()).toBeDisabled();
    await fireEvent.press(screen.getByRole('radio', { name: 'Chest' }));
    await fireEvent.press(screen.getByRole('radio', { name: 'Too tight' }));
    expect(submit()).toBeEnabled();
  });
});

describe('launch', () => {
  test('a signed-in launch opens the closet', async () => {
    const { screen, getPathname } = await renderApp('/');
    expect(await screen.findByText('Grey everyday tee')).toBeTruthy();
    expect(getPathname()).toBe('/closet');
  });

  test('a signed-out launch opens sign-in', async () => {
    const { screen, getPathname } = await renderApp('/', { signedIn: false });
    expect(await screen.findByText(/Will this exact top fit you/)).toBeTruthy();
    expect(getPathname()).toBe('/sign-in');
  });
});
