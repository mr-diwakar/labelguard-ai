"""Deterministic status roll-up. No scoring and no legal verdict language."""

from collections.abc import Sequence

from app.core.enums import ComplianceStatus
from app.schemas.assessment import AssessmentItem


def aggregate_status(
    passed: Sequence[AssessmentItem],
    violations: Sequence[AssessmentItem],
    manual_review: Sequence[AssessmentItem],
) -> ComplianceStatus:
    if violations:
        return ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    if manual_review:
        return ComplianceStatus.MANUAL_REVIEW
    if passed:
        return ComplianceStatus.COMPLIANT
    return ComplianceStatus.MANUAL_REVIEW


def explanation_for(status: ComplianceStatus, *, no_applicable_rules: bool) -> str:
    if no_applicable_rules:
        return (
            "Automated assessment: no verified applicable rules were available for this inspection. "
            "Manual verification recommended. This is not a legal determination."
        )
    if status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE:
        return (
            "Automated assessment: potential non-compliance detected. "
            "Manual verification recommended. This is not a legal determination."
        )
    if status is ComplianceStatus.MANUAL_REVIEW:
        return (
            "Automated assessment: insufficient evidence for a complete determination. "
            "Manual verification recommended. This is not a legal determination."
        )
    return (
        "Automated assessment: no potential non-compliance was identified from the applicable "
        "verified rules. This is not a legal determination."
    )
