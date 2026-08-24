"""
Orchestrates rule resolution and validators. Does not encode individual legal rules.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime

from app.compliance.aggregation import aggregate_status, explanation_for
from app.compliance.registry import ValidatorRegistry, build_default_registry
from app.compliance.resolver import RuleResolver
from app.compliance.validators.support import make_result, rule_id_for
from app.core.enums import ComplianceStatus, ValidationOutcome
from app.core.logging_config import get_logger
from app.schemas.applicability import ApplicabilityReport, ProductContext, RuleApplicability
from app.schemas.assessment import AssessmentItem, ComplianceAssessment, ComplianceRequest
from app.schemas.declaration import Declaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.validation import ValidationContext, ValidationResult

logger = get_logger("compliance")

NO_APPLICABLE_WARNING = "No verified applicable rules were available for this inspection."
MISSING_VALIDATOR_REASON = "No validator is currently implemented for this applicable requirement."
VALIDATOR_FAILURE_REASON = "Validation could not be completed reliably."
UNVERIFIED_REASON = "This rule version is not ACTIVE and VERIFIED, so it is not used as production law."
RESOLUTION_FAILURE_REASON = "Rule resolution could not be completed reliably."
OVERLAP_REASON = "Overlapping rule versions are in force; the resolver will not silently pick one."


class ComplianceEngine:
    def __init__(
        self,
        resolver: RuleResolver,
        registry: ValidatorRegistry | None = None,
    ) -> None:
        self.resolver = resolver
        self.registry = registry or build_default_registry()

    def evaluate(
        self,
        inspection_date: date | datetime | ComplianceRequest,
        product_category: str | None = None,
        product_context: ProductContext | Mapping[str, object] | None = None,
        declarations: Sequence[Declaration] | Mapping[str, object] | None = None,
    ) -> ComplianceAssessment:
        request = (
            inspection_date
            if isinstance(inspection_date, ComplianceRequest)
            else _request_from_parts(inspection_date, product_category, product_context, declarations)
        )
        return self._evaluate(request)

    def _evaluate(self, request: ComplianceRequest) -> ComplianceAssessment:
        context = ProductContext(
            inspection_date=request.inspection_date,
            category=request.product_category,
            is_imported=request.is_imported,
            size_is_relevant=request.size_is_relevant,
        )

        try:
            report = self.resolver.resolve(context)
        except Exception:
            logger.exception("stage=rule_resolver")
            return ComplianceAssessment(
                status=ComplianceStatus.MANUAL_REVIEW,
                warnings=[RESOLUTION_FAILURE_REASON],
                rule_count=0,
                passed_count=0,
                violation_count=0,
                manual_review_count=0,
                not_applicable_count=0,
                explanation=explanation_for(ComplianceStatus.MANUAL_REVIEW, no_applicable_rules=True),
                assessment_confidence=None,
            )

        return self._assess(request, report)

    def _assess(self, request: ComplianceRequest, report: ApplicabilityReport) -> ComplianceAssessment:
        passed: list[AssessmentItem] = []
        violations: list[AssessmentItem] = []
        manual_review: list[AssessmentItem] = []
        not_applicable: list[AssessmentItem] = []
        warnings: list[str] = []
        results: list[AssessmentItem] = []

        validation_context = ValidationContext(
            inspection_date=request.inspection_date,
            category=request.product_category,
            is_imported=request.is_imported,
            size_is_relevant=request.size_is_relevant,
            applicable=True,
            label_readable=request.label_readable,
        )

        for row in report.applicable:
            item = self._evaluate_applicable(row, request.declarations, validation_context)
            results.append(item)
            _bucket(item, passed, violations, manual_review, not_applicable)

        for row in report.not_applicable:
            item = _item_from_applicability(row, ValidationOutcome.NOT_APPLICABLE)
            results.append(item)
            not_applicable.append(item)

        for row in report.unverified:
            item = _item_from_applicability(row, ValidationOutcome.MANUAL_REVIEW, reason=UNVERIFIED_REASON)
            results.append(item)
            manual_review.append(item)
            warnings.append(
                f"{row.rule.rule_code} is not verified and was not treated as production law."
            )

        for row in report.overlaps:
            item = _item_from_applicability(row, ValidationOutcome.MANUAL_REVIEW, reason=row.reason)
            results.append(item)
            manual_review.append(item)
            warnings.append(row.reason)

        for row in report.future:
            warnings.append(
                f"{row.rule.rule_code} is not in force on the inspection date (future version) and was not evaluated."
            )
        for row in report.expired:
            warnings.append(
                f"{row.rule.rule_code} is not in force on the inspection date (expired version) and was not evaluated."
            )

        no_applicable = len(report.applicable) == 0
        if no_applicable:
            warnings.append(NO_APPLICABLE_WARNING)

        status = aggregate_status(passed, violations, manual_review)
        if no_applicable and status is ComplianceStatus.COMPLIANT:
            status = ComplianceStatus.MANUAL_REVIEW

        return ComplianceAssessment(
            status=status,
            passed=passed,
            violations=violations,
            manual_review=manual_review,
            not_applicable=not_applicable,
            warnings=warnings,
            rule_count=len(report.applicable),
            passed_count=len(passed),
            violation_count=len(violations),
            manual_review_count=len(manual_review),
            not_applicable_count=len(not_applicable),
            explanation=explanation_for(status, no_applicable_rules=no_applicable),
            assessment_confidence=None,
            results=results,
        )

    def _evaluate_applicable(
        self,
        row: RuleApplicability,
        declarations: Sequence[Declaration],
        context: ValidationContext,
    ) -> AssessmentItem:
        rule = row.rule
        validator = self.registry.get(rule.validation_type)
        if validator is None:
            result = make_result(rule, ValidationOutcome.MANUAL_REVIEW, MISSING_VALIDATOR_REASON)
            return _item_from_validation(rule, result, row.selected_version)

        try:
            result = validator.validate(rule, declarations, context)
        except Exception:
            logger.exception("stage=validator rule_code=%s", rule.rule_code)
            result = make_result(rule, ValidationOutcome.MANUAL_REVIEW, VALIDATOR_FAILURE_REASON)
            return _item_from_validation(rule, result, row.selected_version)

        return _item_from_validation(rule, result, row.selected_version)


def _request_from_parts(
    inspection_date: date | datetime,
    product_category: str | None,
    product_context: ProductContext | Mapping[str, object] | None,
    declarations: Sequence[Declaration] | Mapping[str, object] | None,
) -> ComplianceRequest:
    extra: dict[str, object] = {}
    if isinstance(product_context, ProductContext):
        extra = {
            "is_imported": product_context.is_imported,
            "size_is_relevant": product_context.size_is_relevant,
        }
        if product_category is None:
            product_category = str(product_context.category)
    elif isinstance(product_context, Mapping):
        extra = dict(product_context)

    if product_category is None:
        raise ValueError("product_category is required when evaluate() is not given a ComplianceRequest.")

    return ComplianceRequest.model_validate(
        {
            "inspection_date": inspection_date,
            "product_category": product_category,
            "is_imported": extra.get("is_imported", False),
            "size_is_relevant": extra.get("size_is_relevant"),
            "label_readable": extra.get("label_readable"),
            "declarations": declarations or [],
        }
    )


def _item_from_validation(
    rule: LegalRuleRecord,
    result: ValidationResult,
    selected_version: str | None,
) -> AssessmentItem:
    return AssessmentItem(
        rule_id=result.rule_id,
        rule_code=result.rule_code,
        rule_name=rule.rule_name,
        source_reference=result.source_reference or rule.source_reference,
        source_document=rule.source_document,
        source_version=rule.source_version,
        selected_version=selected_version or rule.source_version,
        result=result.result,
        confidence=result.confidence,
        reason=result.reason,
        recommended_action=result.recommended_action,
        severity=result.severity,
        evidence=list(result.evidence),
    )


def _item_from_applicability(
    row: RuleApplicability,
    outcome: ValidationOutcome,
    reason: str | None = None,
) -> AssessmentItem:
    rule = row.rule
    return AssessmentItem(
        rule_id=rule_id_for(rule),
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        source_reference=rule.source_reference,
        source_document=rule.source_document,
        source_version=rule.source_version,
        selected_version=row.selected_version,
        result=outcome,
        confidence=None,
        reason=reason or row.reason,
        recommended_action="Manual verification recommended." if outcome is ValidationOutcome.MANUAL_REVIEW else None,
        severity=rule.severity,
    )


def _bucket(
    item: AssessmentItem,
    passed: list[AssessmentItem],
    violations: list[AssessmentItem],
    manual_review: list[AssessmentItem],
    not_applicable: list[AssessmentItem],
) -> None:
    if item.result is ValidationOutcome.PASS:
        passed.append(item)
    elif item.result is ValidationOutcome.POTENTIAL_NON_COMPLIANCE:
        violations.append(item)
    elif item.result is ValidationOutcome.NOT_APPLICABLE:
        not_applicable.append(item)
    else:
        manual_review.append(item)
