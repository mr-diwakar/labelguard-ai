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
}

export interface InspectionSummary {
  total: number;
  compliant: number;
  manualReview: number;
  potentialIssues: number;
}
