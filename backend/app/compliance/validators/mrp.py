from collections.abc import Sequence

from app.compliance.validators.parsing import parse_mrp
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


class MRPValidator:
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
            detected_reason="MRP could not be reliably verified from available evidence.",
        )
        if blocked is not None:
            return blocked

        parsed = parse_mrp(declaration.value or "")
        if parsed is None:
            return make_result(
                rule,
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                "The MRP value could not be parsed as a number.",
                declaration=declaration,
            )
        if parsed.value < 0:
            return make_result(
                rule,
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                "The MRP value is negative.",
                declaration=declaration,
            )

        return make_result(
            rule,
            ValidationOutcome.PASS,
            "MRP declaration detected and parsed successfully.",
            declaration=declaration,
        )
