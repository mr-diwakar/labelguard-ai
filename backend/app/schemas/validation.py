"""One-validator contracts. The future engine aggregates these; it is not defined here."""

from datetime import date, datetime

from pydantic import Field

from app.core.enums import ProductCategory, Severity, ValidationOutcome
from app.schemas.common import APIModel


class ValidationContext(APIModel):
    """
    Facts supplied by the caller. Validators do not load this themselves.

    label_readable=True means the caller already judged the label readable enough
    that a missing field can be treated as absence. It is never inferred from OCR.
    """

    inspection_date: date | datetime | None = None
    category: ProductCategory | str | None = None
    is_imported: bool = False
    size_is_relevant: bool | None = None
    applicable: bool | None = None
    label_readable: bool | None = None
    declaration_fields: list[str] | None = None


class ValidationEvidence(APIModel):
    """Declaration snapshot for a later EvidenceService. Not a generated image."""

    field: str
    value: str | None = None
    source: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    status: str | None = None


class ValidationResult(APIModel):
    """
    Outcome of one requirement check.

    Example:
        {
            "rule_id": "LM-PC-MRP-001",
            "rule_code": "LM-PC-MRP-001",
            "result": "PASS",
            "confidence": 0.75,
            "reason": "Required declaration detected.",
            "evidence": [],
            "recommended_action": null
        }
    """

    rule_id: str
    rule_code: str
    source_reference: str | None = None
    result: ValidationOutcome
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    recommended_action: str | None = None
    severity: Severity = Severity.UNSPECIFIED
