from datetime import date
from typing import Any
from uuid import UUID

from app.core.enums import RuleStatus, Severity, ValidationType, VerificationStatus
from app.schemas.common import APIModel


class LegalRuleRecord(APIModel):
    """Stored rule version. One legal requirement may have many rows over time."""

    id: UUID | None = None
    rule_code: str
    rule_name: str
    description: str
    requirement: str
    category: str
    validation_type: ValidationType | str
    severity: Severity = Severity.UNSPECIFIED
    source_document: str
    source_reference: str | None = None
    source_version: str
    effective_from: date
    effective_to: date | None = None
    applicability_condition: dict[str, Any] | None = None
    rule_status: RuleStatus = RuleStatus.DRAFT
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    is_prototype: bool = True

    def is_authoritative(self) -> bool:
        return (
            self.rule_status is RuleStatus.ACTIVE
            and self.verification_status is VerificationStatus.VERIFIED
        )


class LegalRuleCreate(APIModel):
    rule_code: str
    rule_name: str
    description: str
    requirement: str
    category: str
    validation_type: ValidationType | str
    severity: Severity = Severity.UNSPECIFIED
    source_document: str
    source_reference: str | None = None
    source_version: str
    effective_from: date
    effective_to: date | None = None
    applicability_condition: dict[str, Any] | None = None
    rule_status: RuleStatus = RuleStatus.DRAFT
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    is_prototype: bool = True
