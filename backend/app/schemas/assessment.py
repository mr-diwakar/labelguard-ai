"""Compliance-engine contracts. This is an automated assessment, not a legal judgment."""

from datetime import date, datetime
from typing import Any

from pydantic import Field, model_validator

from app.core.enums import ComplianceStatus, ProductCategory, Severity, ValidationOutcome
from app.schemas.common import APIModel
from app.schemas.declaration import Declaration
from app.schemas.validation import ValidationEvidence


class ComplianceRequest(APIModel):
    """
    Engine input. Declarations may be a list or a field-keyed map.

    Example:
        {
            "inspection_date": "2026-08-23",
            "product_category": "PACKAGED_FOOD",
            "is_imported": false,
            "declarations": {
                "mrp": {"value": "50", "confidence": 0.98, "status": "DETECTED"}
            }
        }
    """

    inspection_date: date | datetime
    product_category: ProductCategory | str
    is_imported: bool = False
    size_is_relevant: bool | None = None
    label_readable: bool | None = None
    declarations: list[Declaration] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_declarations(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = data.get("declarations")
        if raw is None:
            return data
        if isinstance(raw, dict):
            items = [_declaration_payload(field, payload) for field, payload in raw.items()]
            return {**data, "declarations": items}
        if isinstance(raw, list):
            return {**data, "declarations": [_coerce_value(item) for item in raw]}
        return data


def _declaration_payload(field: str, payload: Any) -> Any:
    if isinstance(payload, Declaration):
        return payload
    if isinstance(payload, dict):
        item = {"field": payload.get("field", field), **payload}
        return _coerce_value(item)
    return {"field": field, "value": None if payload is None else str(payload), "status": "DETECTED"}


def _coerce_value(item: Any) -> Any:
    if isinstance(item, dict) and isinstance(item.get("value"), int | float):
        return {**item, "value": str(item["value"])}
    return item


class AssessmentItem(APIModel):
    """One rule outcome, kept for explainability and a later report service."""

    rule_id: str
    rule_code: str
    rule_name: str
    source_reference: str | None = None
    source_document: str | None = None
    source_version: str | None = None
    selected_version: str | None = None
    result: ValidationOutcome
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str
    recommended_action: str | None = None
    severity: Severity = Severity.UNSPECIFIED
    evidence: list[ValidationEvidence] = Field(default_factory=list)


class ComplianceAssessment(APIModel):
    """
    Overall automated assessment. Status values match ComplianceStatus.

    assessment_confidence stays null until a defined methodology exists.
    """

    status: ComplianceStatus
    passed: list[AssessmentItem] = Field(default_factory=list)
    violations: list[AssessmentItem] = Field(default_factory=list)
    manual_review: list[AssessmentItem] = Field(default_factory=list)
    not_applicable: list[AssessmentItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rule_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    violation_count: int = Field(ge=0)
    manual_review_count: int = Field(ge=0)
    not_applicable_count: int = Field(ge=0)
    explanation: str
    assessment_confidence: float | None = None
    results: list[AssessmentItem] = Field(default_factory=list)
