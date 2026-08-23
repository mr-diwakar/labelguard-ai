import { Inspection } from '../types/inspection';

/** Keeps the sample records readable as "today", "yesterday" and so on. */
function daysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);

  return date.toISOString();
}

/**
 * Placeholder content for the UI only. Replace with GET /inspections later;
 * no screen reads inspection data from anywhere else.
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
