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
    LOWER_CARBOHYDRATES = "LOWER_CARBOHYDRATES"
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

