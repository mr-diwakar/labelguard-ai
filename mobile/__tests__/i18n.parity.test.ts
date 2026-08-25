/**
 * Multilingual parity guard (Phase 21.6).
 *
 * Two invariants:
 *  1. All 7 locales expose exactly the same set of leaf keys, so switching
 *     language can never surface a raw key or an English string.
 *  2. Every i18n key the API layer emits at runtime (`declaration.*`,
 *     `verification.check*`, the `live.*` block, stage labels) actually exists in
 *     every locale — those values are fed straight into `t()` by the screens.
 */

import bn from '../i18n/locales/bn.json';
import en from '../i18n/locales/en.json';
import gu from '../i18n/locales/gu.json';
import hi from '../i18n/locales/hi.json';
import mr from '../i18n/locales/mr.json';
import ta from '../i18n/locales/ta.json';
import te from '../i18n/locales/te.json';

const LOCALES: Record<string, unknown> = { en, hi, mr, bn, ta, gu, te };

/** Flatten to dotted leaf paths, e.g. "declaration.mrp". */
function flatten(value: unknown, prefix = ''): string[] {
  if (value === null || typeof value !== 'object') {
    return prefix ? [prefix] : [];
  }
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    flatten(child, prefix ? `${prefix}.${key}` : key),
  );
}

const keysByLocale = Object.fromEntries(
  Object.entries(LOCALES).map(([code, bundle]) => [code, flatten(bundle).sort()]),
) as Record<string, string[]>;

const REFERENCE = 'en';

describe('locale key parity across all 7 languages', () => {
  it('covers every shipped locale file', () => {
    expect(Object.keys(LOCALES).sort()).toEqual(['bn', 'en', 'gu', 'hi', 'mr', 'ta', 'te']);
  });

  it.each(Object.keys(LOCALES).filter((code) => code !== REFERENCE))(
    '%s has exactly the same keys as en',
    (code) => {
      const reference = new Set(keysByLocale[REFERENCE]);
      const candidate = new Set(keysByLocale[code]);
      const missing = keysByLocale[REFERENCE].filter((key) => !candidate.has(key));
      const extra = keysByLocale[code].filter((key) => !reference.has(key));

      expect({ missing, extra }).toEqual({ missing: [], extra: [] });
    },
  );

  it('has no empty translation values', () => {
    for (const [code, bundle] of Object.entries(LOCALES)) {
      const empties: string[] = [];
      const walk = (value: unknown, path: string) => {
        if (value === null || typeof value !== 'object') {
          if (typeof value !== 'string' || value.trim().length === 0) empties.push(path);
          return;
        }
        Object.entries(value as Record<string, unknown>).forEach(([k, v]) =>
          walk(v, path ? `${path}.${k}` : k),
        );
      };
      walk(bundle, '');
      expect({ code, empties }).toEqual({ code, empties: [] });
    }
  });
});

describe('runtime-emitted keys exist in every locale', () => {
  /**
   * Keys produced by api/adapter.ts, data/demoScans.ts, screens/ProcessingScreen.tsx
   * and components/DataSourceNotice.tsx. Listed literally so adding an emitter
   * without adding translations fails here.
   */
  const EMITTED_KEYS = [
    // adapter — declaration labels
    'declaration.mrp',
    'declaration.netQuantity',
    'declaration.manufacturer',
    'declaration.manufacturerAddress',
    'declaration.countryOfOrigin',
    'declaration.name',
    'declaration.date',
    'declaration.consumerCare',
    'declaration.generic',
    // adapter — verification labels
    'verification.checkNetQuantity',
    'verification.checkMrp',
    'verification.checkGeneric',
    // adapter — notices
    'live.legalUnavailable',
    // demo picker labels
    'live.demoClear',
    'live.demoIssue',
    'live.demoMismatch',
    // data-source chip
    'live.demoBadge',
    'live.demoNote',
    'live.apiBadge',
    'live.apiNote',
    // processing stages + outcomes
    'live.stageImage',
    'live.stageOcr',
    'live.stageExtraction',
    'live.stageLegal',
    'live.stageVerification',
    'live.stageGuidance',
    'live.stageNutrition',
    'live.stageCompleted',
    'live.stageSkipped',
    'live.stageFailed',
    // processing errors + retry
    'live.retryTitle',
    'live.retry',
    'live.errorNetwork',
    'live.errorTimeout',
    'live.errorHttp',
    'live.errorMalformed',
    'live.unnamedProduct',
    // camera capture + permission states
    'scan.permissionChecking',
    'scan.permissionTitle',
    'scan.permissionHint',
    'scan.permissionDeniedHint',
    'scan.permissionGrant',
    'scan.capturePhoto',
    'scan.capturing',
    'scan.captureFailed',
    // scan picker copy
    'scan.chooseSampleTitle',
    'scan.chooseSampleHint',
    'processing.loadingTitle',
    'processing.loadingSubtitle',
    'processing.loadingSubtitleImage',
  ];

  it.each(Object.keys(LOCALES))('%s defines every runtime-emitted key', (code) => {
    const present = new Set(keysByLocale[code]);
    const missing = EMITTED_KEYS.filter((key) => !present.has(key));
    expect(missing).toEqual([]);
  });
});
