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
