"""Shared vocabulary for schemas, models and the legal engine."""

from enum import StrEnum


class UserRole(StrEnum):
    INSPECTOR = "INSPECTOR"
    CONSUMER = "CONSUMER"
    ADMIN = "ADMIN"


class ProductCategory(StrEnum):
    PACKAGED_FOOD = "PACKAGED_FOOD"
    COSMETIC = "COSMETIC"
    HOUSEHOLD_PRODUCT = "HOUSEHOLD_PRODUCT"
    ELECTRONIC_PRODUCT = "ELECTRONIC_PRODUCT"
    IMPORTED_PRODUCT = "IMPORTED_PRODUCT"
    OTHER = "OTHER"


class ComplianceStatus(StrEnum):
    COMPLIANT = "COMPLIANT"
    POTENTIAL_NON_COMPLIANCE = "POTENTIAL_NON_COMPLIANCE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class DeclarationStatus(StrEnum):
    """NOT_DETECTED means OCR/extraction found nothing. It is not the same as MISSING."""

    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MANUALLY_VERIFIED = "MANUALLY_VERIFIED"


class DeclarationSource(StrEnum):
    OCR = "OCR"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class Severity(StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ApplicabilityDecision(StrEnum):
    """Outcome of rule selection. This is not a compliance verdict."""

    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXPIRED = "EXPIRED"
    FUTURE = "FUTURE"
    UNVERIFIED = "UNVERIFIED"
    OVERLAP = "OVERLAP"


class ValidationOutcome(StrEnum):
    """
    Result of one validator. Not an inspection status.

    ComplianceStatus stays COMPLIANT / POTENTIAL_NON_COMPLIANCE / MANUAL_REVIEW
    for the future engine. Validators use PASS instead of COMPLIANT.
    """

    PASS = "PASS"
    POTENTIAL_NON_COMPLIANCE = "POTENTIAL_NON_COMPLIANCE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ValidationType(StrEnum):
    REQUIRED_DECLARATION = "REQUIRED_DECLARATION"
    MRP_VALIDATION = "MRP_VALIDATION"
    NET_QUANTITY_VALIDATION = "NET_QUANTITY_VALIDATION"
    DATE_VALIDATION = "DATE_VALIDATION"
    CONSUMER_CARE_VALIDATION = "CONSUMER_CARE_VALIDATION"
    TEXT_FORMAT = "TEXT_FORMAT"
    READABILITY = "READABILITY"
    CONDITIONAL_REQUIREMENT = "CONDITIONAL_REQUIREMENT"


class FindingKind(StrEnum):
    """A stored finding is never a legal verdict; it is either a potential issue or a review flag."""

    POTENTIAL_NON_COMPLIANCE = "POTENTIAL_NON_COMPLIANCE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class EvidenceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class ReportStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"


# --- Multi-product nutrition comparison (Phase 13) ---------------------------
# Deterministic, explainable ranking of already-extracted nutrition values.
# This is an informational comparison, never a health verdict or medical claim.


class NutritionParameter(StrEnum):
    """Canonical nutrition parameters the comparison understands."""

    CALORIES = "CALORIES"
    SUGAR = "SUGAR"
    ADDED_SUGAR = "ADDED_SUGAR"
    PROTEIN = "PROTEIN"
    CARBOHYDRATES = "CARBOHYDRATES"
    FAT = "FAT"
    SATURATED_FAT = "SATURATED_FAT"
    TRANS_FAT = "TRANS_FAT"
    FIBER = "FIBER"
    SODIUM = "SODIUM"


class ParameterDirection(StrEnum):
    """Which way is preferable for a parameter. Fixed per parameter, never taken from a request."""

    LOWER_BETTER = "LOWER_BETTER"
    HIGHER_BETTER = "HIGHER_BETTER"


class NutritionBasis(StrEnum):
    """Reference basis of declared values. Products are only comparable on a shared basis."""

    PER_100G = "PER_100G"
    PER_SERVING = "PER_SERVING"
    UNKNOWN = "UNKNOWN"


class ComparisonPriority(StrEnum):
    """Consumer-selectable priorities. Each maps to a (parameter, direction) during scoring."""

    LOWER_CALORIES = "LOWER_CALORIES"
    LOWER_SUGAR = "LOWER_SUGAR"
    LOWER_ADDED_SUGAR = "LOWER_ADDED_SUGAR"
    HIGHER_PROTEIN = "HIGHER_PROTEIN"
    LOWER_CARBOHYDRATES = "LOWER_CARBOBYDRATES"
    LOWER_FAT = "LOWER_FAT"
    LOWER_SATURATED_FAT = "LOWER_SATURATED_FAT"
    LOWER_TRANS_FAT = "LOWER_TRANS_FAT"
    HIGHER_FIBER = "HIGHER_FIBER"
    LOWER_SODIUM = "LOWER_SODIUM"


class ComparisonOutcome(StrEnum):
    """Per-product ranking outcome. Not a health verdict."""

    RANKED = "RANKED"
    TIED = "TIED"
    COULD_NOT_RANK = "COULD_NOT_RANK"
    SINGLE_PRODUCT = "SINGLE_PRODUCT"


class ComparisonStatus(StrEnum):
    """Overall state of a comparison result."""

    COMPLETED = "COMPLETED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SINGLE_PRODUCT = "SINGLE_PRODUCT"


# ---------------------------------------------------------------------------
# Phase 11 integration-contract vocabularies.
#
# These sit AROUND the legal engine (see app/schemas/contracts/). They are
# additive: the legal core, validators and the declarations DB CHECK constraint
# keep using DeclarationStatus / ComplianceStatus unchanged. Each new enum below
# documents its relationship to the existing vocabulary so there is one source
# of truth and no duplicate status system.
# ---------------------------------------------------------------------------


class DetectionStatus(StrEnum):
    """
    What the extraction/OCR layer concluded about one field.

    Richer than DeclarationStatus on purpose: a field OCR simply failed to read
    (NOT_DETECTED / UNCERTAIN) must stay distinct from a field the extractor is
    confident is absent from a readable label (CONFIRMED_ABSENT).

    This is the extraction-layer vocabulary. It is mapped DOWN to the legal
    engine's DeclarationStatus by app.schemas.contracts.detection; the engine
    itself never sees these values. Mapping:

        DETECTED        -> DeclarationStatus.DETECTED
        UNCERTAIN       -> DeclarationStatus.LOW_CONFIDENCE
        NOT_DETECTED    -> DeclarationStatus.NOT_DETECTED (uncertain absence)
        CONFIRMED_ABSENT-> DeclarationStatus.NOT_DETECTED + high confidence, so the
                           engine's existing is_uncertain() treats it as a
                           reliable absence (requires label_readable=True)
        NOT_APPLICABLE  -> not fed to the engine as a declaration; applicability
                           is decided per-rule by the resolver
    """

    DETECTED = "DETECTED"
    NOT_DETECTED = "NOT_DETECTED"
    CONFIRMED_ABSENT = "CONFIRMED_ABSENT"
    UNCERTAIN = "UNCERTAIN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ObservationSource(StrEnum):
    """
    Where an OBSERVED value came from in label-to-product verification.

    A declared value (from the label/OCR) is never an observation. A normal
    smartphone photo cannot measure mass, so observations arrive from an explicit,
    named source. Implementation of these sources belongs to a later phase.
    """

    CALIBRATED_MEASUREMENT = "CALIBRATED_MEASUREMENT"
    USER_PROVIDED = "USER_PROVIDED"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"
    VERIFIED_OBSERVATION = "VERIFIED_OBSERVATION"
    OTHER = "OTHER"


class VerificationOutcome(StrEnum):
    """
    Result of one label-to-product verification check.

    NOT the same as VerificationStatus (which records whether a legal *rule row*
    is VERIFIED / UNVERIFIED / NEEDS_REVIEW). This enum deliberately avoids that
    name. AI verification must never emit FRAUD / CHEATING / ILLEGAL.
    """

    MATCH = "MATCH"
    POTENTIAL_MISMATCH = "POTENTIAL_MISMATCH"
    COULD_NOT_VERIFY = "COULD_NOT_VERIFY"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceType(StrEnum):
    """Kind of artefact an EvidenceReference points at. Not a generated image."""

    OCR_REGION = "OCR_REGION"
    PRODUCT_IMAGE = "PRODUCT_IMAGE"
    MEASUREMENT = "MEASUREMENT"
    USER_NOTE = "USER_NOTE"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


# ---------------------------------------------------------------------------
# Phase 12 image-intake / OCR vocabularies.
#
# These describe the scan -> image-quality -> preprocessing -> OCR pipeline that
# feeds the Phase 11 OCR contract (app/schemas/ocr.py::OCRResult). They carry NO
# legal meaning: an OCR or quality status is never a compliance verdict, and
# NO_TEXT_DETECTED is never "a declaration is missing" (that decision belongs to
# the later declaration-extraction phase, not Phase 12).
# ---------------------------------------------------------------------------


class ImageQualityStatus(StrEnum):
    """Overall usability of a scanned image for OCR. Not a legal judgement."""

    OK = "OK"
    WARNING = "WARNING"  # usable, but OCR may be less reliable
    UNUSABLE = "UNUSABLE"  # OCR is very unlikely to be reliable


class BrightnessStatus(StrEnum):
    ACCEPTABLE = "ACCEPTABLE"
    TOO_DARK = "TOO_DARK"
    TOO_BRIGHT = "TOO_BRIGHT"


class ResolutionStatus(StrEnum):
    OK = "OK"
    TOO_SMALL = "TOO_SMALL"


class OrientationStatus(StrEnum):
    """Lightweight orientation state, read from EXIF only. No ML model here."""

    OK = "OK"  # no rotation metadata, or already upright
    CORRECTED = "CORRECTED"  # an EXIF rotation was applied to the OCR image
    UNKNOWN = "UNKNOWN"  # could not determine; surfaced as a warning


class OCRStatus(StrEnum):
    """
    Outcome of the OCR stage.

    OCR failure is never legal non-compliance, and NO_TEXT_DETECTED is not the
    same as a missing declaration.
    """

    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_TEXT_DETECTED = "NO_TEXT_DETECTED"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    INVALID_IMAGE = "INVALID_IMAGE"


# ---------------------------------------------------------------------------
# Phase 19 scan-orchestration vocabulary.
#
# Records what each stage of one unified scan did. This is operational status,
# NOT a compliance verdict: a FAILED or SKIPPED stage is a gap in coverage the
# result must surface honestly, never an implied COMPLIANT and never a violation.
# ---------------------------------------------------------------------------


class StageOutcome(StrEnum):
    """How one orchestration stage finished."""

    COMPLETED = "COMPLETED"  # the stage ran and produced its output
    SKIPPED = "SKIPPED"  # the stage did not run (a needed input was absent)
    FAILED = "FAILED"  # the stage errored; the scan continues with partial results
