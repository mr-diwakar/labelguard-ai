import { Inspection } from '../types/inspection';

/** Keeps the sample records readable as "today", "yesterday" and so on. */
function daysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);

  return date.toISOString();
}

/**
 * Placeholder content for the UI only.
 *
 * This is the single mock data source for the consumer result experience:
 * legal assessment, label-to-product verification and evidence all hang off
 * one inspection record. Replace the bodies of the accessors below with the
 * scan / inspection / verification / evidence API calls when they exist; no
 * screen should read inspection data from anywhere else.
 *
 * The five records deliberately cover every result state the UI must handle:
 *   insp-001  POTENTIAL_MISMATCH   (declared vs observed differ)
 *   insp-002  MATCH                (successful verification)
 *   insp-003  MANUAL_REVIEW        (human check recommended)
 *   insp-004  MATCH, no confidence (missing-confidence handling)
 *   insp-005  COULD_NOT_VERIFY + empty evidence list
 */
export const mockInspections: Inspection[] = [
  {
    id: 'insp-001',
    productName: 'Britannia Product',
    category: 'Bakery',
    inspectedAt: daysAgo(0),
    assessment: {
      status: 'POTENTIAL_NON_COMPLIANCE',
      confidence: 0.91,
      ruleReference: 'Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)',
      passed: [
        { declarationKey: 'declaration.mrp', confidence: 0.97 },
        { declarationKey: 'declaration.netQuantity', confidence: 0.94 },
      ],
      violations: [
        {
          declarationKey: 'declaration.manufacturerAddress',
          confidence: 0.89,
          boundingBox: { x: 0.12, y: 0.54, width: 0.66, height: 0.16 },
        },
      ],
      manualReview: [],
    },
    verification: {
      status: 'POTENTIAL_MISMATCH',
      confidence: 0.94,
      checks: [
        {
          id: 'chk-001-q',
          type: 'QUANTITY',
          labelKey: 'verification.checkNetQuantity',
          declared: '500 g',
          observed: '472 g',
          difference: '28 g',
          method: 'USER_MEASUREMENT',
          confidence: 0.94,
          status: 'POTENTIAL_MISMATCH',
          boundingBox: { x: 0.12, y: 0.54, width: 0.66, height: 0.16 },
          evidenceId: 'ev-001-measure',
        },
        {
          id: 'chk-001-mrp',
          type: 'TEXT_VALUE',
          labelKey: 'verification.checkMrp',
          declared: '₹50',
          observed: '₹50',
          method: 'OCR',
          confidence: 0.97,
          status: 'MATCH',
          evidenceId: 'ev-001-label',
        },
      ],
    },
    evidence: [
      {
        id: 'ev-001-label',
        type: 'LABEL_IMAGE',
        titleKey: 'evidence.typeLabelImage',
        boundingBox: { x: 0.12, y: 0.54, width: 0.66, height: 0.16 },
        capturedAt: daysAgo(0),
      },
      {
        id: 'ev-001-measure',
        type: 'MEASUREMENT',
        titleKey: 'evidence.typeMeasurement',
        expectedValue: '500 g',
        observedValue: '472 g',
        confidence: 0.94,
        note: 'Weighed on a kitchen scale.',
        capturedAt: daysAgo(0),
      },
      {
        id: 'ev-001-region',
        type: 'HIGHLIGHTED_REGION',
        titleKey: 'evidence.typeHighlighted',
        boundingBox: { x: 0.12, y: 0.54, width: 0.66, height: 0.16 },
        capturedAt: daysAgo(0),
      },
    ],
  },
  {
    id: 'insp-002',
    productName: 'Tata Salt',
    category: 'Staples',
    inspectedAt: daysAgo(1),
    assessment: {
      status: 'COMPLIANT',
      confidence: 0.96,
      ruleReference: 'Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)',
      passed: [
        { declarationKey: 'declaration.mrp', confidence: 0.98 },
        { declarationKey: 'declaration.netQuantity', confidence: 0.97 },
        { declarationKey: 'declaration.manufacturer', confidence: 0.95 },
        { declarationKey: 'declaration.countryOfOrigin', confidence: 0.92 },
      ],
      violations: [],
      manualReview: [],
    },
    verification: {
      status: 'MATCH',
      confidence: 0.97,
      checks: [
        {
          id: 'chk-002-q',
          type: 'QUANTITY',
          labelKey: 'verification.checkNetQuantity',
          declared: '1 kg',
          observed: '1 kg',
          difference: '0 g',
          method: 'USER_MEASUREMENT',
          confidence: 0.98,
          status: 'MATCH',
          evidenceId: 'ev-002-measure',
        },
        {
          id: 'chk-002-mrp',
          type: 'TEXT_VALUE',
          labelKey: 'verification.checkMrp',
          declared: '₹28',
          observed: '₹28',
          method: 'OCR',
          confidence: 0.96,
          status: 'MATCH',
          evidenceId: 'ev-002-label',
        },
      ],
    },
    evidence: [
      {
        id: 'ev-002-label',
        type: 'LABEL_IMAGE',
        titleKey: 'evidence.typeLabelImage',
        capturedAt: daysAgo(1),
      },
      {
        id: 'ev-002-measure',
        type: 'MEASUREMENT',
        titleKey: 'evidence.typeMeasurement',
        expectedValue: '1 kg',
        observedValue: '1 kg',
        confidence: 0.98,
        capturedAt: daysAgo(1),
      },
    ],
  },
  {
    id: 'insp-003',
    productName: 'Sample Product',
    category: 'Beverages',
    inspectedAt: daysAgo(2),
    assessment: {
      status: 'MANUAL_REVIEW',
      confidence: 0.62,
      ruleReference: 'Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 8',
      passed: [{ declarationKey: 'declaration.mrp', confidence: 0.88 }],
      violations: [],
      manualReview: [
        {
          declarationKey: 'declaration.netQuantity',
          confidence: 0.54,
          boundingBox: { x: 0.18, y: 0.32, width: 0.44, height: 0.14 },
        },
      ],
    },
    verification: {
      status: 'MANUAL_REVIEW',
      confidence: 0.55,
      checks: [
        {
          id: 'chk-003-q',
          type: 'QUANTITY',
          labelKey: 'verification.checkNetQuantity',
          declared: '1 L',
          observed: '0.96 L',
          difference: '0.04 L',
          method: 'USER_MEASUREMENT',
          confidence: 0.55,
          status: 'MANUAL_REVIEW',
          boundingBox: { x: 0.18, y: 0.32, width: 0.44, height: 0.14 },
          evidenceId: 'ev-003-region',
        },
      ],
    },
    evidence: [
      {
        id: 'ev-003-region',
        type: 'HIGHLIGHTED_REGION',
        titleKey: 'evidence.typeHighlighted',
        boundingBox: { x: 0.18, y: 0.32, width: 0.44, height: 0.14 },
        confidence: 0.54,
        capturedAt: daysAgo(2),
      },
      {
        id: 'ev-003-note',
        type: 'NOTE',
        titleKey: 'evidence.typeNote',
        note: 'Label text was partially obscured; recommend re-checking the net quantity by hand.',
        capturedAt: daysAgo(2),
      },
    ],
  },
  {
    id: 'insp-004',
    productName: 'Aashirvaad Atta',
    category: 'Staples',
    inspectedAt: daysAgo(4),
    assessment: {
      status: 'COMPLIANT',
      confidence: 0.93,
      passed: [
        { declarationKey: 'declaration.mrp', confidence: 0.95 },
        { declarationKey: 'declaration.netQuantity', confidence: 0.93 },
        { declarationKey: 'declaration.manufacturer', confidence: 0.91 },
      ],
      violations: [],
      manualReview: [],
    },
    verification: {
      // Overall confidence intentionally omitted to exercise missing-confidence UI.
      status: 'MATCH',
      checks: [
        {
          id: 'chk-004-q',
          type: 'QUANTITY',
          labelKey: 'verification.checkNetQuantity',
          declared: '5 kg',
          observed: '5 kg',
          difference: '0 g',
          method: 'USER_MEASUREMENT',
          // confidence intentionally omitted
          status: 'MATCH',
          evidenceId: 'ev-004-measure',
        },
      ],
    },
    evidence: [
      {
        id: 'ev-004-label',
        type: 'LABEL_IMAGE',
        titleKey: 'evidence.typeLabelImage',
        capturedAt: daysAgo(4),
      },
      {
        id: 'ev-004-measure',
        type: 'MEASUREMENT',
        titleKey: 'evidence.typeMeasurement',
        expectedValue: '5 kg',
        observedValue: '5 kg',
        // confidence intentionally omitted
        capturedAt: daysAgo(4),
      },
    ],
  },
  {
    id: 'insp-005',
    productName: 'Local Snack Pack',
    category: 'Snacks',
    inspectedAt: daysAgo(8),
    assessment: {
      status: 'MANUAL_REVIEW',
      confidence: 0.58,
      passed: [{ declarationKey: 'declaration.manufacturer', confidence: 0.86 }],
      violations: [],
      manualReview: [
        {
          declarationKey: 'declaration.mrp',
          confidence: 0.49,
          boundingBox: { x: 0.24, y: 0.62, width: 0.38, height: 0.12 },
        },
      ],
    },
    verification: {
      // No overall confidence and no observed value: evidence was insufficient.
      status: 'COULD_NOT_VERIFY',
      checks: [
        {
          id: 'chk-005-q',
          type: 'QUANTITY',
          labelKey: 'verification.checkNetQuantity',
          declared: '60 g',
          method: 'OCR',
          status: 'COULD_NOT_VERIFY',
        },
      ],
    },
    // Empty on purpose: exercises the empty-evidence state and the add flow.
    evidence: [],
  },
];

export const mockMandatoryDeclarations: string[] = [
  'declaration.declarations',
  'declaration.mrp',
  'declaration.netQuantity',
  'declaration.manufacturer',
];

export function findMockInspection(id: string): Inspection | undefined {
  return mockInspections.find((inspection) => inspection.id === id);
}
