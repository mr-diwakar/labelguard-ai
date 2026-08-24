"""Deterministic legal-engine output. An LLM must never produce this object directly."""

from pydantic import Field

from app.core.enums import ComplianceStatus, Severity
from app.schemas.common import APIModel


class ComplianceFinding(APIModel):
    """
    One potential issue or manual-review item.

    Example:
        {
            "rule_id": "LM-PC-001",
            "rule_code": "MRP_DECLARATION",
            "description": "Potential issue detected",
            "severity": "HIGH",
            "confidence": 0.91,
            "evidence_reference": null,
            "recommended_action": "Manual verification recommended."
        }
    """

    rule_id: str
    rule_code: str
    description: str
    severity: Severity
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_reference: str | None = None
    recommended_action: str = "Manual verification recommended."


class ComplianceResult(APIModel):
    """
    Engine result stored with an inspection.

    Example:
        {
            "status": "POTENTIAL_NON_COMPLIANCE",
            "rules_evaluated": 8,
            "passed": 6,
            "potential_violations": 1,
            "manual_review": 1,
            "violations": [],
            "manual_review_items": []
        }
    """

    status: ComplianceStatus
    rules_evaluated: int = Field(ge=0)
    passed: int = Field(ge=0)
    potential_violations: int = Field(ge=0)
    manual_review: int = Field(ge=0)
    violations: list[ComplianceFinding] = Field(default_factory=list)
    manual_review_items: list[ComplianceFinding] = Field(default_factory=list)
    explanation: str | None = None
