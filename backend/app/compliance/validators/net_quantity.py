from collections.abc import Sequence

from app.compliance.validators.parsing import parse_quantity_or_number
from app.compliance.validators.support import (
    gate_rule,
    make_result,
    pick_declaration,
    presence_outcome,
    resolve_fields,
)
from app.core.enums import ValidationOutcome
from app.schemas.declaration import Declaration
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.validation import ValidationContext, ValidationResult


class NetQuantityValidator:
    def validate(
        self,
        rule: LegalRuleRecord,
        declarations: Sequence[Declaration],
        context: ValidationContext,
    ) -> ValidationResult:
        gated = gate_rule(rule, context)
        if gated is not None:
            return gated

        declaration = pick_declaration(declarations, resolve_fields(rule, context))
        blocked = presence_outcome(
            rule,
            declaration,
            context,
            detected_reason="Net quantity could not be reliably verified from available evidence.",
        )
        if blocked is not None:
            return blocked

        parsed, number_only = parse_quantity_or_number(declaration.value or "")
        if number_only:
            return make_result(
                rule,
                ValidationOutcome.MANUAL_REVIEW,
                "A numeric quantity was found without a unit.",
                declaration=declaration,
            )
        if parsed is None:
            return make_result(
                rule,
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                "The net-quantity value is not a positive number with a recognised unit.",
                declaration=declaration,
            )
        if parsed.value <= 0:
            return make_result(
                rule,
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                "The net-quantity value is not positive.",
                declaration=declaration,
            )

        return make_result(
            rule,
            ValidationOutcome.PASS,
            f"Net quantity detected and parsed as {parsed.value} {parsed.unit}.",
            declaration=declaration,
        )
