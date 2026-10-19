import type { ZoneResultModel } from '@/api/schema';
import { colors } from '@/theme';

import {
  confidenceBadge,
  formatCm,
  formatDiff,
  formatEase,
  formatEaseShort,
  labelColor,
  productDisplayName,
  zoneDisplayName,
} from './format';

function zone(partial: Partial<ZoneResultModel> & { zone: ZoneResultModel['zone'] }): ZoneResultModel {
  return { label: 'regular', basis: 'reference', confidence: 'high', ...partial };
}

describe('formatCm', () => {
  it('prints whole centimetres without decimals', () => {
    expect(formatCm(4)).toBe('4 cm');
    expect(formatCm(12.3)).toBe('12 cm');
  });
  it('keeps one decimal under 10 cm', () => {
    expect(formatCm(2.5)).toBe('2.5 cm');
  });
  it('adds a plus sign when asked and a proper minus', () => {
    expect(formatCm(4, { signed: true })).toBe('+4 cm');
    expect(formatCm(-2, { signed: true })).toBe('−2 cm');
    expect(formatCm(-0.01, { signed: true })).toBe('0 cm');
  });
});

describe('formatEase', () => {
  it('describes more room vs the reference', () => {
    expect(formatEase(zone({ zone: 'chest', delta_vs_ref_cm: 4 }), 'grey tee')).toBe(
      '4 cm more room at the chest than your grey tee',
    );
  });
  it('describes less room vs the reference', () => {
    expect(formatEase(zone({ zone: 'hem', delta_vs_ref_cm: -2 }), 'grey tee')).toBe(
      '2 cm less room at the hem than your grey tee',
    );
  });
  it('says same when the delta rounds to zero', () => {
    expect(formatEase(zone({ zone: 'shoulder', delta_vs_ref_cm: 0.04 }), 'grey tee')).toBe(
      'Same as your grey tee across the shoulders',
    );
  });
  it('falls back to ease when there is no reference', () => {
    expect(formatEase(zone({ zone: 'chest', ease_cm: 4, basis: 'body' }), null)).toBe('4 cm ease at the chest');
    expect(formatEase(zone({ zone: 'bicep', ease_cm: -1.5, basis: 'body' }))).toBe(
      '1.5 cm negative ease around the upper arm',
    );
  });
  it('uses the position text for length and sleeve', () => {
    expect(
      formatEase(
        zone({
          zone: 'length',
          label: null,
          position: { landmark: 'hip_line', offset_cm: 2, text: 'Ends 2 cm below your hip line' },
        }),
        'grey tee',
      ),
    ).toBe('Ends 2 cm below your hip line');
  });
  it('falls back to the label when no numbers exist', () => {
    expect(formatEase(zone({ zone: 'collar', label: 'fitted' }))).toBe('Fitted at the collar');
  });
});

describe('formatEaseShort', () => {
  it('shows a signed delta against the reference', () => {
    expect(formatEaseShort(zone({ zone: 'chest', delta_vs_ref_cm: 4 }), 'grey tee')).toBe('+4 cm vs your grey tee');
  });
  it('shows ease without a reference', () => {
    expect(formatEaseShort(zone({ zone: 'chest', ease_cm: 6 }))).toBe('6 cm ease');
  });
});

describe('labels, zones, confidence', () => {
  it('maps labels to theme colours', () => {
    expect(labelColor('tight')).toBe(colors.label.tight);
    expect(labelColor('relaxed')).toBe(colors.label.relaxed);
    expect(labelColor(null)).toBe(colors.textMuted);
  });
  it('gives every zone a display name', () => {
    expect(zoneDisplayName('bicep')).toBe('Upper arm');
    expect(zoneDisplayName('hem')).toBe('Hem');
  });
  it('builds a confidence badge', () => {
    expect(confidenceBadge('high')).toMatchObject({ text: 'High confidence', color: colors.confidence.high });
    expect(confidenceBadge('low').hint).toMatch(/Measure a tee/);
  });
  it('formats what-would-change diffs', () => {
    expect(formatDiff('chest', 3)).toBe('Chest: +3 cm');
    expect(formatDiff('length', 0)).toBe('Length: no change');
  });
});

describe('productDisplayName', () => {
  it('prefers the stored title', () => {
    expect(productDisplayName({ title: 'Heavyweight Tee', url_canonical: 'https://x.com/products/a' })).toBe('Heavyweight Tee');
  });
  it('falls back to the product slug', () => {
    expect(productDisplayName({ title: null, url_canonical: 'https://shop.example.com/products/heavyweight-tee' })).toBe('Heavyweight tee');
    expect(productDisplayName({ url_original: 'https://www.brand.com/en/p/oxford_shirt.html?x=1' })).toBe('Oxford shirt');
  });
  it('falls back to the host name', () => {
    expect(productDisplayName({ url_canonical: 'https://www.brand.com/products/12345' })).toBe('brand.com');
  });
});
