/**
 * Deterministic demo inputs for a **real** scan.
 *
 * There is no camera and no bundled OCR provider in this build, so a scan cannot
 * start from a photo (see `mobile/api/types.ts`). Instead each entry here is a
 * hand-written `ScanRequest` — structured OCR text plus optional verification
 * input — that is POSTed unchanged to the real `/api/v1/scan`. The backend engine
 * produces the verdict; nothing here asserts an outcome.
 *
 * HONESTY: the comments describe only the INPUT (what label text is present or
 * absent, what value was measured). They never claim the engine will return a
 * violation/mismatch — that is the pipeline's decision and is surfaced live.
 */

import type { OCRResult, ScanRequest } from '../api/types';

export type DemoScanKey = 'clear' | 'issue' | 'mismatch';

/** Used by "Verify Again" when the source inspection has no recorded demo key. */
export const DEFAULT_DEMO_KEY: DemoScanKey = 'clear';

export interface DemoScan {
  key: DemoScanKey;
  /** i18n key for the picker label. */
  labelKey: string;
  request: ScanRequest;
}

function ocr(text: string, confidence: number, bbox: [number, number, number, number]): OCRResult {
  return { text, confidence, bbox };
}

const PACKAGED_FOOD = 'PACKAGED_FOOD';

/**
 * (a) A well-formed label: every commonly-required declaration is present and
 * clearly phrased. The engine assesses it against the active rule set.
 */
const CLEAR: DemoScan = {
  key: 'clear',
  labelKey: 'live.demoClear',
  request: {
    scan_id: 'demo-clear',
    context: {
      inspection_datetime: '2026-08-25',
      product_category: PACKAGED_FOOD,
      label_readable: true,
    },
    product: { name: 'Demo Cookies 200 g', category: 'Packaged food' },
    ocr_results: [
      ocr('Demo Cookies', 0.96, [40, 30, 300, 70]),
      ocr('MRP ₹ 45 (incl. of all taxes)', 0.95, [40, 90, 320, 120]),
      ocr('Net Quantity: 200 g', 0.95, [40, 130, 300, 160]),
      ocr('Manufactured by: Demo Foods Pvt Ltd, Plot 12, Industrial Area, Pune 411001', 0.92, [40, 170, 520, 210]),
      ocr('Mfg Date: 05/2026', 0.93, [40, 220, 260, 250]),
      ocr('Country of Origin: India', 0.94, [40, 260, 320, 290]),
      ocr('Consumer Care: care@demofoods.example, 1800-000-000', 0.9, [40, 300, 520, 330]),
    ],
  },
};

/**
 * (b) The same product, but the manufacturer-address and consumer-care lines are
 * absent from the OCR text, and `label_readable` is true — so the engine assesses
 * the label as readable and evaluates the presence of each required declaration
 * rather than deferring everything to manual review. What it concludes is its call.
 */
const ISSUE: DemoScan = {
  key: 'issue',
  labelKey: 'live.demoIssue',
  request: {
    scan_id: 'demo-issue',
    context: {
      inspection_datetime: '2026-08-25',
      product_category: PACKAGED_FOOD,
      label_readable: true,
    },
    product: { name: 'Demo Snack 100 g', category: 'Packaged food' },
    ocr_results: [
      ocr('Demo Snack', 0.95, [40, 30, 300, 70]),
      ocr('MRP ₹ 20 (incl. of all taxes)', 0.94, [40, 90, 320, 120]),
      ocr('Net Quantity: 100 g', 0.94, [40, 130, 300, 160]),
      ocr('Country of Origin: India', 0.93, [40, 170, 320, 200]),
    ],
  },
};

/**
 * (c) A clear label declaring 500 g, paired with a user-supplied measured value
 * of 472 g. The verification layer compares declared vs observed and decides the
 * outcome; the measurement is flagged USER_PROVIDED so the app never implies a
 * camera weighed the product.
 */
const MISMATCH: DemoScan = {
  key: 'mismatch',
  labelKey: 'live.demoMismatch',
  request: {
    scan_id: 'demo-mismatch',
    context: {
      inspection_datetime: '2026-08-25',
      product_category: PACKAGED_FOOD,
      label_readable: true,
    },
    product: { name: 'Demo Grains 500 g', category: 'Packaged food' },
    ocr_results: [
      ocr('Demo Grains', 0.96, [40, 30, 300, 70]),
      ocr('MRP ₹ 90 (incl. of all taxes)', 0.95, [40, 90, 320, 120]),
      ocr('Net Quantity: 500 g', 0.95, [40, 130, 300, 160]),
      ocr('Manufactured by: Demo Foods Pvt Ltd, Plot 12, Industrial Area, Pune 411001', 0.92, [40, 170, 520, 210]),
      ocr('Country of Origin: India', 0.94, [40, 220, 320, 250]),
    ],
    verification_inputs: [
      {
        field: 'net_quantity',
        expected: { value: 500, unit: 'g' },
        observed: { value: 472, unit: 'g' },
        observation_confidence: 0.9,
        observation_source: 'USER_PROVIDED',
      },
    ],
  },
};

export const demoScans: Record<DemoScanKey, DemoScan> = {
  clear: CLEAR,
  issue: ISSUE,
  mismatch: MISMATCH,
};

/** Ordered for the picker UI. */
export const DEMO_SCAN_ORDER: DemoScanKey[] = ['clear', 'issue', 'mismatch'];

/**
 * Build the request to send for a demo key, stamping the inspection datetime with
 * the current time so the result reads as a fresh scan. Called only at runtime.
 */
export function buildDemoRequest(key: DemoScanKey): ScanRequest {
  const demo = demoScans[key];
  const { context } = demo.request;
  return {
    ...demo.request,
    context: context ? { ...context, inspection_datetime: new Date().toISOString() } : context,
  };
}
