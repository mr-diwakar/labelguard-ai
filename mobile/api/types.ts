/**
 * TypeScript mirror of the backend scan contracts, in the backend's own
 * **snake_case**. This is the ONLY place the app speaks snake_case: the client
 * sends these shapes to `POST /api/v1/scan` and receives `ScanResult`, and the
 * adapter (`./adapter`) converts a `ScanResult` into the camelCase domain
 * `Inspection` the screens render. Keeping the wire shapes isolated here means a
 * backend field rename is a one-file change.
 *
 * Source of truth (do not diverge without checking these):
 *   - app/schemas/contracts/scan.py       ScanRequest / ScanResult / ScanStageStatus
 *   - app/schemas/contracts/context.py    InspectionContext
 *   - app/schemas/assessment.py           ComplianceAssessment / AssessmentItem
 *   - app/schemas/contracts/verification  VerificationInput / VerificationResult / MeasuredValue
 *   - app/schemas/contracts/evidence.py   EvidenceReference
 *   - app/schemas/contracts/guidance.py   ConsumerGuidance / GuidanceItem
 *   - app/schemas/contracts/nutrition.py  NutritionFacts / NutritionValue
 *   - app/schemas/contracts/product.py    ProductProfile
 *   - app/schemas/ingredient.py           IngredientItem
 *   - app/schemas/contracts/detection.py  ExtractedDeclaration
 *   - app/schemas/ocr.py                  OCRResult
 *   - app/core/enums.py                   the string enums below
 *
 * The backend model is `extra="forbid"` for INPUT: an unknown key on a
 * `ScanRequest` is rejected with HTTP 422, so these request shapes must not
 * carry fields the backend does not declare.
 */

// --- Enums (string-literal unions mirroring app/core/enums.py) ------------- //

export type ComplianceStatus =
  | 'COMPLIANT'
  | 'POTENTIAL_NON_COMPLIANCE'
  | 'MANUAL_REVIEW';

export type ProductCategory =
  | 'PACKAGED_FOOD'
  | 'COSMETIC'
  | 'HOUSEHOLD_PRODUCT'
  | 'ELECTRONIC_PRODUCT'
  | 'IMPORTED_PRODUCT'
  | 'OTHER';

export type ValidationOutcome =
  | 'PASS'
  | 'POTENTIAL_NON_COMPLIANCE'
  | 'MANUAL_REVIEW'
  | 'NOT_APPLICABLE';

export type Severity = 'UNSPECIFIED' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type VerificationOutcome =
  | 'MATCH'
  | 'POTENTIAL_MISMATCH'
  | 'COULD_NOT_VERIFY'
  | 'MANUAL_REVIEW'
  | 'NOT_APPLICABLE';

export type ObservationSource =
  | 'CALIBRATED_MEASUREMENT'
  | 'USER_PROVIDED'
  | 'EXTERNAL_EVIDENCE'
  | 'VERIFIED_OBSERVATION'
  | 'OTHER';

export type EvidenceType =
  | 'OCR_REGION'
  | 'PRODUCT_IMAGE'
  | 'MEASUREMENT'
  | 'USER_NOTE'
  | 'DOCUMENT'
  | 'OTHER';

export type StageOutcome = 'COMPLETED' | 'SKIPPED' | 'FAILED';

export type DetectionStatus =
  | 'DETECTED'
  | 'NOT_DETECTED'
  | 'CONFIRMED_ABSENT'
  | 'UNCERTAIN'
  | 'NOT_APPLICABLE';

export type FindingKind = 'POTENTIAL_NON_COMPLIANCE' | 'MANUAL_REVIEW';

/** OCR bounding box in image PIXELS: [x1, y1, x2, y2]. */
export type PixelBBox = [number, number, number, number];

// --- Leaf contracts -------------------------------------------------------- //

export interface OCRResult {
  text: string;
  /** 0..1. */
  confidence: number;
  bbox: PixelBBox;
}

export interface MeasuredValue {
  value: number;
  unit?: string | null;
}

export interface EvidenceReference {
  evidence_id: string;
  evidence_type: EvidenceType;
  source?: string | null;
  image_reference?: string | null;
  /** PIXELS [x1, y1, x2, y2]; dropped by the adapter (no image dims to normalise). */
  bbox?: PixelBBox | null;
  /** ISO 8601. */
  timestamp?: string | null;
  note?: string | null;
  /** 0..1. */
  confidence?: number | null;
}

/** One field the OCR/extraction layer produced. */
export interface ExtractedDeclaration {
  field: string;
  value?: string | null;
  unit?: string | null;
  confidence?: number | null;
  status: DetectionStatus;
  source?: string;
  source_reference?: string | null;
  bbox?: number[] | null;
}

/** Declaration snapshot behind one assessment item. Its `field` is the most
 *  precise signal for choosing a consumer-facing declaration label. */
export interface ValidationEvidence {
  field: string;
  value?: string | null;
  source?: string | null;
  confidence?: number | null;
  bbox?: number[] | null;
  status?: string | null;
}

export interface AssessmentItem {
  rule_id: string;
  rule_code: string;
  rule_name: string;
  source_reference?: string | null;
  source_document?: string | null;
  source_version?: string | null;
  selected_version?: string | null;
  result: ValidationOutcome;
  /** 0..1. */
  confidence?: number | null;
  reason: string;
  recommended_action?: string | null;
  severity?: Severity;
  evidence?: ValidationEvidence[];
}

export interface ComplianceAssessment {
  status: ComplianceStatus;
  passed: AssessmentItem[];
  violations: AssessmentItem[];
  manual_review: AssessmentItem[];
  not_applicable: AssessmentItem[];
  warnings: string[];
  rule_count: number;
  passed_count: number;
  violation_count: number;
  manual_review_count: number;
  not_applicable_count: number;
  explanation: string;
  /** 0..1. */
  assessment_confidence?: number | null;
  results: AssessmentItem[];
}

export interface VerificationInput {
  field: string;
  expected: MeasuredValue;
  observed?: MeasuredValue | null;
  /** 0..1. */
  observation_confidence?: number | null;
  observation_source?: ObservationSource | null;
  expected_source_reference?: string | null;
  observed_source_reference?: string | null;
  evidence?: EvidenceReference[];
}

export interface VerificationResult {
  field: string;
  expected: MeasuredValue;
  observed?: MeasuredValue | null;
  status: VerificationOutcome;
  difference?: number | null;
  /** 0..1. */
  observation_confidence?: number | null;
  observation_source?: ObservationSource | null;
  method?: string | null;
  applicable_rule_code?: string | null;
  evidence?: EvidenceReference[];
  note?: string | null;
}

export interface GuidanceItem {
  issue: string;
  finding_kind: FindingKind;
  severity?: Severity;
  source_reference?: string | null;
  detail?: string | null;
  recommended_evidence?: EvidenceReference[];
  next_steps?: string[];
  limitations?: string[];
}

export interface ConsumerGuidance {
  status: ComplianceStatus;
  headline: string;
  items?: GuidanceItem[];
  what_we_found?: string[];
  why_it_matters?: string[];
  what_is_uncertain?: string[];
  what_evidence_to_keep?: EvidenceReference[];
  what_you_can_do_next?: string[];
  limitations?: string[];
  disclaimer: string;
}

/** amount is null when the value is unknown — NEVER coerce a missing value to 0. */
export interface NutritionValue {
  amount?: number | null;
  unit?: string | null;
  status?: DetectionStatus | null;
  source_reference?: string | null;
}

export interface NutritionFacts {
  basis?: string | null;
  serving_size?: string | null;
  energy?: NutritionValue | null;
  protein?: NutritionValue | null;
  carbohydrates?: NutritionValue | null;
  total_sugar?: NutritionValue | null;
  added_sugar?: NutritionValue | null;
  fat?: NutritionValue | null;
  saturated_fat?: NutritionValue | null;
  trans_fat?: NutritionValue | null;
  fiber?: NutritionValue | null;
  sodium?: NutritionValue | null;
}

export interface ProductProfile {
  name?: string | null;
  brand?: string | null;
  category?: ProductCategory | string | null;
  net_quantity?: string | null;
  mrp?: string | null;
  barcode?: string | null;
  product_identifier?: string | null;
}

export interface IngredientItem {
  name: string;
  raw_text?: string | null;
  normalized_name?: string | null;
  position?: number | null;
  confidence?: number | null;
  source_reference?: string | null;
}

export interface InspectionContext {
  inspection_id?: string | null;
  /** ISO date or datetime. REQUIRED by the backend when a context is supplied. */
  inspection_datetime: string;
  /** REQUIRED by the backend when a context is supplied. */
  product_category: ProductCategory | string;
  product_identifier?: string | null;
  source?: string | null;
  rule_version_context?: string | null;
  is_imported?: boolean;
  size_is_relevant?: boolean | null;
  label_readable?: boolean | null;
}

export interface ScanStageStatus {
  stage: string;
  status: StageOutcome;
  detail?: string | null;
}

// --- Top-level request / response ----------------------------------------- //

/**
 * Everything is optional; `{}` is a valid request. `ocr_results` is how a scan
 * begins — the backend has no raw-image endpoint here (no OCR provider bundled),
 * so the client supplies already-structured OCR JSON. `extra="forbid"` on the
 * backend means no extra keys may be added to this object.
 */
export interface ScanRequest {
  scan_id?: string | null;
  context?: InspectionContext | null;
  ocr_results?: OCRResult[];
  verification_inputs?: VerificationInput[];
  nutrition?: NutritionFacts | null;
  product?: ProductProfile | null;
  ingredients?: IngredientItem[];
  evidence?: EvidenceReference[];
}

export interface ScanResult {
  scan_id: string;
  context?: InspectionContext | null;
  product?: ProductProfile | null;
  declarations: ExtractedDeclaration[];
  legal_assessment?: ComplianceAssessment | null;
  verification: VerificationResult[];
  guidance?: ConsumerGuidance | null;
  nutrition?: NutritionFacts | null;
  ingredients: IngredientItem[];
  evidence: EvidenceReference[];
  stages: ScanStageStatus[];
  warnings: string[];
}
