/**
 * The one bridge from the backend wire contract to the app's domain model.
 *
 * `scanResultToInspection` is a **pure** function: same input → same output, no
 * `fetch`, no globals beyond an optional `now` for timestamps. Everything the
 * screens render is produced here, so every edge case the UI relies on is a rule
 * enforced in this file (each is called out at its mapping):
 *
 *   - `legal_assessment == null` (legal stage SKIPPED/FAILED) is NEVER rendered
 *     as COMPLIANT — it becomes MANUAL_REVIEW plus a "legal not available" notice.
 *   - A `list<VerificationResult>` collapses to the single `verification.checks[]`
 *     the screens expect; the overall status is the **highest-severity** check so
 *     `ResultScreen`'s `checks.find(c => c.status === verification.status)` resolves.
 *   - `null` backend values become `undefined` (the components branch on
 *     `=== undefined`, e.g. muted "could not verify" text).
 *   - A physical-quantity observation reads as USER_MEASUREMENT only when the
 *     backend says it was measured — never fabricating that a camera weighed it.
 *   - Pixel bounding boxes are dropped (no image dimensions to normalise into the
 *     0..1 boxes the overlay expects) rather than invented.
 *
 * `declarationKey` / `labelKey` values are fed straight into i18next `t()` by
 * `LegalCheckList` / `DeclaredObservedRow`, so this file only ever emits keys
 * that exist in every locale (see the `declaration.*` / `verification.*` blocks).
 */

import type {
  AssessmentItem,
  ComplianceAssessment,
  EvidenceReference,
  EvidenceType as ApiEvidenceType,
  MeasuredValue,
  ObservationSource,
  ScanResult,
  VerificationResult as ApiVerificationResult,
} from './types';
import type {
  DeclarationCheck,
  EvidenceItem,
  EvidenceType,
  Inspection,
  InspectionAssessment,
  VerificationCheck,
  VerificationCheckType,
  VerificationMethod,
  VerificationOutcome,
  VerificationResult,
} from '../types/inspection';

export interface ScanAdapterOptions {
  /** ISO timestamp used for any value the backend left unset. Tests pass a fixed value. */
  now?: string;
  /** Whether this inspection came from the live API or a demo record. Default 'API'. */
  source?: 'DEMO' | 'API';
  /** Shown as the product name when the result carries none. */
  fallbackProductName?: string;
}

// --------------------------------------------------------------------------- //
// Declaration label resolution (must yield a real i18n key)
// --------------------------------------------------------------------------- //

/** Declaration field name (from validation evidence) → `declaration.*` i18n key. */
const FIELD_TO_DECLARATION_KEY: Record<string, string> = {
  mrp: 'declaration.mrp',
  retail_sale_price: 'declaration.mrp',
  net_quantity: 'declaration.netQuantity',
  manufacturer: 'declaration.manufacturer',
  packer: 'declaration.manufacturer',
  importer: 'declaration.manufacturer',
  manufacturer_address: 'declaration.manufacturerAddress',
  country_of_origin: 'declaration.countryOfOrigin',
  origin: 'declaration.countryOfOrigin',
  commodity_name: 'declaration.name',
  name: 'declaration.name',
  manufacture_date: 'declaration.date',
  packing_date: 'declaration.date',
  import_date: 'declaration.date',
  date: 'declaration.date',
  consumer_care: 'declaration.consumerCare',
  consumer_complaint: 'declaration.consumerCare',
  care: 'declaration.consumerCare',
};

/** Fallback when no evidence field is present: infer from the rule_code substring. */
function declarationKeyFromRuleCode(ruleCode: string): string | undefined {
  const code = ruleCode.toUpperCase();
  if (code.includes('MRP')) return 'declaration.mrp';
  if (code.includes('NETQ') || code.includes('QUANTITY')) return 'declaration.netQuantity';
  if (code.includes('MFR') || code.includes('MANUF')) return 'declaration.manufacturer';
  if (code.includes('ORIGIN')) return 'declaration.countryOfOrigin';
  if (code.includes('NAME')) return 'declaration.name';
  if (code.includes('DATE')) return 'declaration.date';
  if (code.includes('CARE') || code.includes('COMPLAINT')) return 'declaration.consumerCare';
  return undefined;
}

function declarationKeyFor(item: AssessmentItem): string {
  const field = item.evidence?.[0]?.field;
  if (field) {
    const byField = FIELD_TO_DECLARATION_KEY[field.toLowerCase()];
    if (byField) return byField;
  }
  return declarationKeyFromRuleCode(item.rule_code) ?? 'declaration.generic';
}

function assessmentItemToCheck(item: AssessmentItem): DeclarationCheck {
  return {
    declarationKey: declarationKeyFor(item),
    note: item.reason || undefined,
    confidence: item.confidence ?? undefined,
    // Pixel bbox from validation evidence is intentionally dropped (no image dims).
  };
}

/**
 * Legal assessment → the required `assessment` field. A missing assessment is
 * MANUAL_REVIEW, never COMPLIANT (safety invariant: absence of a check is not a pass).
 */
function legalToAssessment(legal: ComplianceAssessment | null | undefined): {
  assessment: InspectionAssessment;
  notice?: string;
} {
  if (!legal) {
    return {
      assessment: { status: 'MANUAL_REVIEW', passed: [], violations: [], manualReview: [] },
      notice: 'live.legalUnavailable',
    };
  }

  const ruleReference =
    legal.results.find((item) => item.source_reference)?.source_reference ?? undefined;

  return {
    assessment: {
      status: legal.status,
      confidence: legal.assessment_confidence ?? undefined,
      ruleReference,
      passed: legal.passed.map(assessmentItemToCheck),
      violations: legal.violations.map(assessmentItemToCheck),
      manualReview: legal.manual_review.map(assessmentItemToCheck),
    },
  };
}

// --------------------------------------------------------------------------- //
// Verification: list<VerificationResult> → one VerificationResult (checks[])
// --------------------------------------------------------------------------- //

/** Highest-severity-first ranking. The overall status is the worst single check. */
const VERIFICATION_SEVERITY: Record<VerificationOutcome, number> = {
  POTENTIAL_MISMATCH: 0,
  MANUAL_REVIEW: 1,
  COULD_NOT_VERIFY: 2,
  MATCH: 3,
  NOT_APPLICABLE: 4,
};

function formatNumber(value: number): string {
  if (Number.isInteger(value)) return String(value);
  // Trim floating-point noise from a computed difference without over-rounding.
  return String(Number(value.toFixed(3)));
}

function formatMeasured(value: MeasuredValue | null | undefined): string | undefined {
  if (!value) return undefined;
  return value.unit ? `${formatNumber(value.value)} ${value.unit}` : formatNumber(value.value);
}

function checkTypeFor(field: string): VerificationCheckType {
  const f = field.toLowerCase();
  if (f === 'net_quantity' || f.includes('weight') || f.includes('volume')) return 'QUANTITY';
  if (f.includes('count') || f.includes('pieces') || f.includes('units')) return 'COUNT';
  if (f.includes('name') || f.includes('identifier') || f.includes('identity')) return 'PRODUCT_IDENTITY';
  if (f.includes('mrp') || f.includes('price')) return 'TEXT_VALUE';
  return 'OTHER';
}

function verificationLabelKey(field: string): string {
  const f = field.toLowerCase();
  if (f === 'net_quantity') return 'verification.checkNetQuantity';
  if (f.includes('mrp') || f.includes('retail_sale_price') || f.includes('price')) {
    return 'verification.checkMrp';
  }
  return 'verification.checkGeneric';
}

/**
 * Observed-value provenance. USER_MEASUREMENT is used ONLY when the backend
 * explicitly says the observation was measured — so `VerificationScreen`'s
 * "a phone camera cannot weigh a product" notice fires exactly when a real
 * measurement backs a quantity, and never merely because a value was present.
 */
function methodFor(source: ObservationSource | null | undefined, hasObserved: boolean): VerificationMethod | undefined {
  switch (source) {
    case 'CALIBRATED_MEASUREMENT':
    case 'USER_PROVIDED':
      return 'USER_MEASUREMENT';
    case 'VERIFIED_OBSERVATION':
    case 'EXTERNAL_EVIDENCE':
    case 'OTHER':
      return 'MANUAL';
    default:
      // No stated source: a present value was read from the label (OCR); nothing
      // observed means no method to report.
      return hasObserved ? 'OCR' : undefined;
  }
}

function verificationResultToCheck(result: ApiVerificationResult, index: number): VerificationCheck {
  const observed = formatMeasured(result.observed);
  const difference =
    result.difference != null ? formatMeasured({ value: Math.abs(result.difference), unit: result.observed?.unit ?? result.expected?.unit ?? null }) : undefined;

  return {
    id: `vchk-${index}-${result.field}`,
    type: checkTypeFor(result.field),
    labelKey: verificationLabelKey(result.field),
    declared: formatMeasured(result.expected),
    observed,
    difference,
    method: methodFor(result.observation_source, observed !== undefined),
    confidence: result.observation_confidence ?? undefined,
    status: result.status,
    evidenceId: result.evidence?.[0]?.evidence_id,
    // Pixel bbox dropped rather than fabricated into a 0..1 overlay box.
  };
}

function verificationToResult(results: ApiVerificationResult[]): VerificationResult | undefined {
  if (results.length === 0) {
    return undefined; // screens degrade to COULD_NOT_VERIFY / EmptyState.
  }

  const checks = results.map(verificationResultToCheck);
  const worst = checks.reduce((acc, check) =>
    VERIFICATION_SEVERITY[check.status] < VERIFICATION_SEVERITY[acc.status] ? check : acc,
  );

  return {
    status: worst.status,
    confidence: worst.confidence,
    checks,
  };
}

// --------------------------------------------------------------------------- //
// Evidence: ScanResult.evidence ∪ each VerificationResult.evidence, deduped
// --------------------------------------------------------------------------- //

const EVIDENCE_TYPE_MAP: Record<ApiEvidenceType, EvidenceType> = {
  OCR_REGION: 'HIGHLIGHTED_REGION',
  PRODUCT_IMAGE: 'PRODUCT_IMAGE',
  MEASUREMENT: 'MEASUREMENT',
  USER_NOTE: 'NOTE',
  DOCUMENT: 'NOTE',
  OTHER: 'NOTE',
};

function evidenceRefToItem(ref: EvidenceReference, fallbackTime: string): EvidenceItem {
  return {
    id: ref.evidence_id,
    type: EVIDENCE_TYPE_MAP[ref.evidence_type] ?? 'NOTE',
    imageRef: ref.image_reference ?? undefined,
    note: ref.note ?? undefined,
    confidence: ref.confidence ?? undefined,
    capturedAt: ref.timestamp ?? fallbackTime,
    // titleKey omitted so the card falls back to a type label; pixel bbox dropped.
  };
}

function collectEvidence(result: ScanResult, fallbackTime: string): EvidenceItem[] {
  const seen = new Set<string>();
  const items: EvidenceItem[] = [];

  const consider = (ref: EvidenceReference) => {
    if (seen.has(ref.evidence_id)) return;
    seen.add(ref.evidence_id);
    items.push(evidenceRefToItem(ref, fallbackTime));
  };

  result.evidence.forEach(consider);
  result.verification.forEach((v) => (v.evidence ?? []).forEach(consider));

  return items;
}

// --------------------------------------------------------------------------- //
// Top-level
// --------------------------------------------------------------------------- //

function resolveProductName(result: ScanResult, fallback: string): string {
  const candidates = [
    result.product?.name,
    result.product?.product_identifier,
    result.context?.product_identifier,
  ];
  for (const candidate of candidates) {
    const trimmed = candidate?.trim();
    if (trimmed) return trimmed;
  }
  return fallback;
}

export function scanResultToInspection(result: ScanResult, options: ScanAdapterOptions = {}): Inspection {
  const now = options.now ?? new Date().toISOString();
  const source = options.source ?? 'API';
  const fallbackName = options.fallbackProductName ?? 'Scanned product';

  const { assessment, notice } = legalToAssessment(result.legal_assessment);
  const verification = verificationToResult(result.verification);
  const evidence = collectEvidence(result, now);

  const notices = notice ? [notice] : [];

  const category = typeof result.product?.category === 'string' ? result.product.category : undefined;

  return {
    id: result.scan_id,
    productName: resolveProductName(result, fallbackName),
    inspectedAt: result.context?.inspection_datetime ?? now,
    category,
    assessment,
    verification,
    evidence: evidence.length > 0 ? evidence : undefined,
    source,
    notices: notices.length > 0 ? notices : undefined,
    warnings: result.warnings.length > 0 ? result.warnings : undefined,
  };
}
