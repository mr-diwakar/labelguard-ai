/**
 * Shapes here mirror what the FastAPI service is expected to return, so screens
 * keep their props unchanged once GET /inspections and POST /scan replace the
 * mock data.
 */

export type ComplianceStatus =
  | 'COMPLIANT'
  | 'POTENTIAL_NON_COMPLIANCE'
  | 'MANUAL_REVIEW';

/** Normalised 0..1 coordinates so the overlay scales to any image size. */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DeclarationCheck {
  /** Translation key when the value comes from the mock layer. */
  declarationKey: string;
  /** Free text from the backend, shown as-is when present. */
  note?: string;
  /** 0..1 for this individual check. */
  confidence?: number;
  boundingBox?: BoundingBox;
}

export interface InspectionAssessment {
  status: ComplianceStatus;
  /** 0..1, absent when the backend cannot score the assessment. */
  confidence?: number;
  /** Legal Metrology clause the assessment was made against. */
  ruleReference?: string;
  passed: DeclarationCheck[];
  violations: DeclarationCheck[];
  manualReview: DeclarationCheck[];
}

export interface Inspection {
  id: string;
  productName: string;
  /** ISO timestamp; the UI formats it into a localised relative label. */
  inspectedAt: string;
  category?: string;
  assessment: InspectionAssessment;
  /**
   * Label-to-product verification (declared claim vs observed value).
   * Optional: absent until the verification API (Phase 11) exists, in which
   * case the result screen treats it as "could not verify".
   */
  verification?: VerificationResult;
  /** Evidence artefacts. Absent or empty when none were captured/generated. */
  evidence?: EvidenceItem[];
  /**
   * Where this record came from: 'API' = a live scan through the backend,
   * 'DEMO' = a bundled sample record. Absent on legacy records (treated as demo).
   */
  source?: 'DEMO' | 'API';
  /**
   * i18n keys for advisory notices about missing/partial data (e.g. the legal
   * stage was skipped). Rendered as localized lines, never as an error.
   */
  notices?: string[];
  /** Raw backend warning strings (already human-readable), shown as-is when present. */
  warnings?: string[];
}

export interface InspectionSummary {
  total: number;
  compliant: number;
  manualReview: number;
  potentialIssues: number;
}

/**
 * Label-to-product verification result states.
 *
 * These are intentionally distinct from the legal `ComplianceStatus` above and
 * from the backend rule-row `VerificationStatus` enum (which means whether a
 * legal rule row is VERIFIED/UNVERIFIED). See PROJECT_CONTEXT §7–8: never
 * conflate a MATCH/MISMATCH verification result with either of those.
 */
export type VerificationOutcome =
  | 'MATCH'
  | 'POTENTIAL_MISMATCH'
  | 'MANUAL_REVIEW'
  | 'COULD_NOT_VERIFY'
  | 'NOT_APPLICABLE';

export type VerificationCheckType =
  | 'QUANTITY'
  | 'COUNT'
  | 'TEXT_VALUE'
  | 'PRODUCT_IDENTITY'
  | 'OTHER';

/**
 * How the observed value was obtained. A phone camera can never measure
 * physical mass, so mass always comes from USER_MEASUREMENT, not the camera.
 */
export type VerificationMethod = 'OCR' | 'USER_MEASUREMENT' | 'COMPUTER_VISION' | 'MANUAL';

export interface VerificationCheck {
  id: string;
  type: VerificationCheckType;
  /** Translation key for the consumer-facing label of this check. */
  labelKey: string;
  /** Expected value read from the label/declaration (already unit-formatted). */
  declared?: string;
  /** Observed value from a measurement, computer vision or manual entry. */
  observed?: string;
  /** Human-readable difference, e.g. "28 g". */
  difference?: string;
  method?: VerificationMethod;
  /** 0..1 for this individual check; absent when it cannot be scored. */
  confidence?: number;
  status: VerificationOutcome;
  boundingBox?: BoundingBox;
  /** Links this check to an EvidenceItem.id when supporting evidence exists. */
  evidenceId?: string;
}

export interface VerificationResult {
  /** Aggregated outcome across all checks. */
  status: VerificationOutcome;
  /** 0..1, absent when the result cannot be scored. */
  confidence?: number;
  checks: VerificationCheck[];
}

export type EvidenceType =
  | 'PRODUCT_IMAGE'
  | 'LABEL_IMAGE'
  | 'HIGHLIGHTED_REGION'
  | 'MEASUREMENT'
  | 'NOTE';

/**
 * One evidence artefact. Extends the current backend `EvidenceItem` contract
 * (id, bbox, notes) with the label-to-product fields listed in PROJECT_CONTEXT
 * §14 (type, expected/observed value, confidence, timestamp) that the evidence
 * service is planned to add.
 */
export interface EvidenceItem {
  id: string;
  type: EvidenceType;
  /** Translation key for a seed item's title, when the title is localised. */
  titleKey?: string;
  /** Free-text title, used for user-added evidence. */
  title?: string;
  /** Image URI/path placeholder; absent renders the placeholder frame. */
  imageRef?: string;
  boundingBox?: BoundingBox;
  expectedValue?: string;
  observedValue?: string;
  /** 0..1. */
  confidence?: number;
  note?: string;
  /** ISO timestamp. */
  capturedAt: string;
  /** True when produced by the preview build rather than a real capture/upload. */
  isPlaceholder?: boolean;
}
