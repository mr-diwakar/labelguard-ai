/**
 * Unit tests for the wire→domain adapter (`scanResultToInspection`).
 *
 * These lock in the safety-relevant mapping rules the screens depend on:
 * missing legal ≠ compliant, list→single verification with worst-severity
 * overall, null→undefined, USER_MEASUREMENT only when the backend measured it,
 * evidence dedupe, and pixel-bbox drop. Pure logic, no React Native.
 */

import { scanResultToInspection } from '../api/adapter';
import type {
  AssessmentItem,
  ComplianceAssessment,
  ScanResult,
  VerificationResult,
} from '../api/types';

const NOW = '2026-08-25T10:00:00.000Z';

function item(overrides: Partial<AssessmentItem> = {}): AssessmentItem {
  return {
    rule_id: 'r1',
    rule_code: 'GENERIC_RULE',
    rule_name: 'Generic rule',
    result: 'PASS',
    reason: 'ok',
    ...overrides,
  };
}

function assessment(overrides: Partial<ComplianceAssessment> = {}): ComplianceAssessment {
  return {
    status: 'COMPLIANT',
    passed: [],
    violations: [],
    manual_review: [],
    not_applicable: [],
    warnings: [],
    rule_count: 0,
    passed_count: 0,
    violation_count: 0,
    manual_review_count: 0,
    not_applicable_count: 0,
    explanation: '',
    results: [],
    ...overrides,
  };
}

function scanResult(overrides: Partial<ScanResult> = {}): ScanResult {
  return {
    scan_id: 'scan-1',
    declarations: [],
    verification: [],
    ingredients: [],
    evidence: [],
    stages: [],
    warnings: [],
    ...overrides,
  };
}

describe('scanResultToInspection — legal assessment', () => {
  it('maps a present legal assessment, resolving declaration keys by field then rule_code', () => {
    const legal = assessment({
      status: 'POTENTIAL_NON_COMPLIANCE',
      assessment_confidence: 0.8,
      passed: [item({ rule_code: 'MRP_PRESENT', evidence: [{ field: 'mrp' }] })],
      violations: [item({ rule_code: 'MFR_ADDRESS_MISSING', result: 'POTENTIAL_NON_COMPLIANCE', reason: 'address missing' })],
      manual_review: [item({ rule_code: 'SOMETHING_ODD', result: 'MANUAL_REVIEW' })],
      results: [item({ source_reference: 'LM Rule 6' })],
    });

    const out = scanResultToInspection(scanResult({ legal_assessment: legal }), { now: NOW });

    expect(out.assessment.status).toBe('POTENTIAL_NON_COMPLIANCE');
    expect(out.assessment.confidence).toBe(0.8);
    expect(out.assessment.ruleReference).toBe('LM Rule 6');
    // field 'mrp' → declaration.mrp
    expect(out.assessment.passed[0].declarationKey).toBe('declaration.mrp');
    // no evidence field → inferred from rule_code substring 'MFR'
    expect(out.assessment.violations[0].declarationKey).toBe('declaration.manufacturer');
    expect(out.assessment.violations[0].note).toBe('address missing');
    // unrecognised rule_code → generic fallback key
    expect(out.assessment.manualReview[0].declarationKey).toBe('declaration.generic');
  });

  it('treats a null legal assessment as MANUAL_REVIEW with a notice — NEVER compliant', () => {
    const out = scanResultToInspection(scanResult({ legal_assessment: null }), { now: NOW });

    expect(out.assessment.status).toBe('MANUAL_REVIEW');
    expect(out.assessment.status).not.toBe('COMPLIANT');
    expect(out.assessment.passed).toEqual([]);
    expect(out.assessment.violations).toEqual([]);
    expect(out.assessment.manualReview).toEqual([]);
    expect(out.notices).toContain('live.legalUnavailable');
  });

  it('converts a null assessment confidence to undefined (never 0)', () => {
    const legal = assessment({
      passed: [item({ evidence: [{ field: 'net_quantity' }], confidence: null })],
    });
    const out = scanResultToInspection(scanResult({ legal_assessment: legal }), { now: NOW });
    expect(out.assessment.passed[0].confidence).toBeUndefined();
    expect(out.assessment.passed[0].declarationKey).toBe('declaration.netQuantity');
  });
});

describe('scanResultToInspection — verification list → single result', () => {
  function vr(overrides: Partial<VerificationResult>): VerificationResult {
    return {
      field: 'net_quantity',
      expected: { value: 500, unit: 'g' },
      status: 'MATCH',
      ...overrides,
    };
  }

  it('collapses a list to checks[] and takes the highest-severity overall status', () => {
    const out = scanResultToInspection(
      scanResult({
        verification: [
          vr({ field: 'mrp', expected: { value: 90, unit: null }, status: 'MATCH', observation_confidence: 0.99 }),
          vr({ field: 'net_quantity', observed: { value: 472, unit: 'g' }, difference: -28, status: 'POTENTIAL_MISMATCH', observation_confidence: 0.9, observation_source: 'USER_PROVIDED' }),
        ],
      }),
      { now: NOW },
    );

    expect(out.verification).toBeDefined();
    // POTENTIAL_MISMATCH outranks MATCH.
    expect(out.verification!.status).toBe('POTENTIAL_MISMATCH');
    expect(out.verification!.confidence).toBe(0.9);
    expect(out.verification!.checks).toHaveLength(2);

    const netQ = out.verification!.checks.find((c) => c.type === 'QUANTITY')!;
    expect(netQ.declared).toBe('500 g');
    expect(netQ.observed).toBe('472 g');
    expect(netQ.difference).toBe('28 g'); // abs value, formatted with unit
    expect(netQ.labelKey).toBe('verification.checkNetQuantity');
    // USER_PROVIDED → USER_MEASUREMENT (drives the "camera can't weigh" notice).
    expect(netQ.method).toBe('USER_MEASUREMENT');
    expect(netQ.status).toBe('POTENTIAL_MISMATCH');
  });

  it('returns undefined verification for an empty backend list', () => {
    const out = scanResultToInspection(scanResult({ verification: [] }), { now: NOW });
    expect(out.verification).toBeUndefined();
  });

  it('reports method OCR for an unsourced observed value, and undefined when nothing was observed', () => {
    const out = scanResultToInspection(
      scanResult({
        verification: [
          vr({ field: 'mrp', expected: { value: 90, unit: null }, observed: { value: 90, unit: null }, status: 'MATCH' }),
          vr({ field: 'count', expected: { value: 6, unit: null }, observed: null, status: 'COULD_NOT_VERIFY' }),
        ],
      }),
      { now: NOW },
    );
    const withObserved = out.verification!.checks.find((c) => c.type === 'TEXT_VALUE')!;
    const withoutObserved = out.verification!.checks.find((c) => c.type === 'COUNT')!;
    expect(withObserved.method).toBe('OCR');
    expect(withoutObserved.observed).toBeUndefined();
    expect(withoutObserved.method).toBeUndefined();
  });
});

describe('scanResultToInspection — evidence & top-level', () => {
  it('unions and dedupes evidence by id and drops pixel bboxes', () => {
    const out = scanResultToInspection(
      scanResult({
        evidence: [
          { evidence_id: 'E1', evidence_type: 'OCR_REGION', bbox: [1, 2, 3, 4], note: 'region' },
        ],
        verification: [
          {
            field: 'net_quantity',
            expected: { value: 500, unit: 'g' },
            status: 'MATCH',
            evidence: [
              { evidence_id: 'E1', evidence_type: 'OCR_REGION' }, // duplicate id
              { evidence_id: 'E2', evidence_type: 'MEASUREMENT', confidence: null },
            ],
          },
        ],
      }),
      { now: NOW },
    );

    expect(out.evidence).toHaveLength(2);
    const ids = out.evidence!.map((e) => e.id);
    expect(ids).toEqual(['E1', 'E2']);
    // Type mapped, no boundingBox fabricated from pixel bbox, null confidence → undefined.
    expect(out.evidence![0].type).toBe('HIGHLIGHTED_REGION');
    expect(out.evidence![0].boundingBox).toBeUndefined();
    expect(out.evidence![1].confidence).toBeUndefined();
    expect(out.evidence![0].capturedAt).toBe(NOW); // no timestamp → fallback time
  });

  it('resolves product name with fallback and forwards warnings', () => {
    const named = scanResultToInspection(
      scanResult({ product: { name: '  Demo Cookies  ' } }),
      { now: NOW },
    );
    expect(named.productName).toBe('Demo Cookies');

    const unnamed = scanResultToInspection(scanResult({ warnings: ['legal stage skipped'] }), {
      now: NOW,
      fallbackProductName: 'Unnamed',
    });
    expect(unnamed.productName).toBe('Unnamed');
    expect(unnamed.warnings).toEqual(['legal stage skipped']);
    expect(unnamed.source).toBe('API'); // default source
  });

  it('marks the record source explicitly when told it is DEMO', () => {
    const out = scanResultToInspection(scanResult(), { now: NOW, source: 'DEMO' });
    expect(out.source).toBe('DEMO');
  });
});
