"""Shared presence, evidence, and result helpers. No legal conclusions live here."""

from collections.abc import Sequence

from app.compliance.applicability import context_category_tokens, matches_any_category
from app.core.enums import DeclarationStatus, ValidationOutcome
from app.schemas.declaration import Declaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.validation import ValidationContext, ValidationEvidence, ValidationResult

# Below this, NOT_DETECTED / empty extraction is treated as uncertainty, never absence.
UNCERTAIN_CONFIDENCE_MAX = 0.6

# Assessment confidence is not OCR confidence.
ASSESSMENT_PASS = 0.75
ASSESSMENT_PASS_MANUAL = 0.90
ASSESSMENT_FAIL = 0.80
ASSESSMENT_FAIL_MANUAL = 0.90
ASSESSMENT_REVIEW = 0.40
ASSESSMENT_NOT_APPLICABLE = 1.0

REVIEW_ACTION = "Manual verification recommended."

# Application field aliases. These are not government field names.
RULE_FIELDS: dict[str, tuple[str, ...]] = {
    "LM-PC-MFR-001": ("manufacturer", "packer", "importer", "manufacturer_address"),
    "LM-PC-NAME-001": ("commodity_name", "name"),
    "LM-PC-NETQ-001": ("net_quantity",),
    "LM-PC-DATE-001": ("manufacture_date", "packing_date", "import_date", "date"),
    "LM-PC-MRP-001": ("mrp", "retail_sale_price"),
    "LM-PC-CARE-001": ("consumer_care", "consumer_complaint", "care"),
    "LM-PC-ORIGIN-001": ("country_of_origin", "origin"),
}

TYPE_FIELDS: dict[str, tuple[str, ...]] = {
    "MRP_VALIDATION": ("mrp", "retail_sale_price"),
    "NET_QUANTITY_VALIDATION": ("net_quantity",),
    "DATE_VALIDATION": ("manufacture_date", "packing_date", "import_date", "date"),
    "CONSUMER_CARE_VALIDATION": ("consumer_care", "consumer_complaint", "care"),
}


def rule_id_for(rule: LegalRuleRecord) -> str:
    return str(rule.id) if rule.id is not None else rule.rule_code


def evidence_from(declaration: Declaration | None) -> list[ValidationEvidence]:
    if declaration is None:
        return []

    return [
        ValidationEvidence(
            field=declaration.field,
            value=declaration.value,
            source=str(declaration.source),
            confidence=declaration.confidence,
            bbox=declaration.bbox,
            status=str(declaration.status),
        )
    ]


def assessment_confidence(outcome: ValidationOutcome, declaration: Declaration | None) -> float:
    if outcome is ValidationOutcome.NOT_APPLICABLE:
        return ASSESSMENT_NOT_APPLICABLE
    if outcome is ValidationOutcome.MANUAL_REVIEW:
        if declaration is not None and declaration.confidence is not None:
            return min(declaration.confidence, ASSESSMENT_REVIEW)
        return ASSESSMENT_REVIEW
    if outcome is ValidationOutcome.PASS:
        if declaration is not None and declaration.status is DeclarationStatus.MANUALLY_VERIFIED:
            return ASSESSMENT_PASS_MANUAL
        return ASSESSMENT_PASS
    if declaration is not None and declaration.status is DeclarationStatus.MANUALLY_VERIFIED:
        return ASSESSMENT_FAIL_MANUAL
    return ASSESSMENT_FAIL


def make_result(
    rule: LegalRuleRecord,
    outcome: ValidationOutcome,
    reason: str,
    *,
    declaration: Declaration | None = None,
    recommended_action: str | None = None,
) -> ValidationResult:
    if recommended_action is None and outcome in {
        ValidationOutcome.MANUAL_REVIEW,
        ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
    }:
        recommended_action = REVIEW_ACTION

    return ValidationResult(
        rule_id=rule_id_for(rule),
        rule_code=rule.rule_code,
        source_reference=rule.source_reference,
        result=outcome,
        confidence=assessment_confidence(outcome, declaration),
        reason=reason,
        evidence=evidence_from(declaration),
        recommended_action=recommended_action,
        severity=rule.severity,
    )


def resolve_fields(rule: LegalRuleRecord, context: ValidationContext) -> tuple[str, ...]:
    if context.declaration_fields:
        return tuple(item.lower() for item in context.declaration_fields)

    recorded = (rule.applicability_condition or {}).get("declaration_fields")
    if recorded:
        return tuple(str(item).lower() for item in recorded)

    mapped = RULE_FIELDS.get(rule.rule_code)
    if mapped:
        return mapped

    return TYPE_FIELDS.get(str(rule.validation_type), ())


def pick_declaration(
    declarations: Sequence[Declaration],
    fields: Sequence[str],
) -> Declaration | None:
    wanted = {item.lower() for item in fields}
    matches = [item for item in declarations if item.field.lower() in wanted]
    if not matches:
        return None

    rank = {
        DeclarationStatus.MANUALLY_VERIFIED: 0,
        DeclarationStatus.DETECTED: 1,
        DeclarationStatus.LOW_CONFIDENCE: 2,
        DeclarationStatus.NOT_DETECTED: 3,
    }
    return sorted(
        matches,
        key=lambda item: (rank.get(item.status, 9), -(item.confidence or 0)),
    )[0]


def is_uncertain(declaration: Declaration | None, context: ValidationContext) -> bool:
    if declaration is None:
        return context.label_readable is not True

    if declaration.status is DeclarationStatus.LOW_CONFIDENCE:
        return True

    if declaration.confidence is not None and declaration.confidence < UNCERTAIN_CONFIDENCE_MAX:
        return True

    if declaration.status is DeclarationStatus.NOT_DETECTED:
        reliable_absence = (
            context.label_readable is True
            and declaration.confidence is not None
            and declaration.confidence >= UNCERTAIN_CONFIDENCE_MAX
        )
        return not reliable_absence

    return False


def gate_rule(rule: LegalRuleRecord, context: ValidationContext) -> ValidationResult | None:
    if context.applicable is False:
        return make_result(
            rule,
            ValidationOutcome.NOT_APPLICABLE,
            "This rule does not apply to the current product context.",
        )

    if context.applicable is not True and context.category is not None:
        tokens = context_category_tokens(str(context.category), context.is_imported)
        if not matches_any_category(rule.category, rule.applicability_condition, tokens):
            return make_result(
                rule,
                ValidationOutcome.NOT_APPLICABLE,
                "The product category is outside this rule version's recorded applicability.",
            )
        condition = (rule.applicability_condition or {}).get("condition")
        if condition == "ONLY_WHEN_SIZE_IS_RELEVANT" and context.size_is_relevant is not True:
            return make_result(
                rule,
                ValidationOutcome.NOT_APPLICABLE,
                "This requirement applies only when the sizes of the commodity are relevant.",
            )

    if not rule.is_authoritative():
        return make_result(
            rule,
            ValidationOutcome.MANUAL_REVIEW,
            "This rule version is not ACTIVE and VERIFIED, so it is not used as production law.",
        )

    return None


def presence_outcome(
    rule: LegalRuleRecord,
    declaration: Declaration | None,
    context: ValidationContext,
    *,
    detected_reason: str,
) -> ValidationResult | None:
    """
    Shared presence gate.

    NOT_DETECTED is never treated as a legal gap unless the caller also marks
    the label readable and extraction confidence is not in the uncertain band.
    """
    if is_uncertain(declaration, context):
        return make_result(
            rule,
            ValidationOutcome.MANUAL_REVIEW,
            "The required declaration could not be reliably verified from available evidence.",
            declaration=declaration,
        )

    if declaration is None or declaration.status is DeclarationStatus.NOT_DETECTED:
        return make_result(
            rule,
            ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
            "Reliable evidence indicates the required declaration is absent.",
            declaration=declaration,
        )

    if not (declaration.value or "").strip():
        return make_result(
            rule,
            ValidationOutcome.MANUAL_REVIEW,
            "A declaration was recorded without a usable value.",
            declaration=declaration,
        )

    if declaration.status in {DeclarationStatus.DETECTED, DeclarationStatus.MANUALLY_VERIFIED}:
        return None

    return make_result(
        rule,
        ValidationOutcome.MANUAL_REVIEW,
        detected_reason,
        declaration=declaration,
    )
