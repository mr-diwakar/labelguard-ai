from collections.abc import Sequence

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


class RequiredDeclarationValidator:
    def validate(
        self,
        rule: LegalRuleRecord,
        declarations: Sequence[Declaration],
        context: ValidationContext,
    ) -> ValidationResult:
        gated = gate_rule(rule, context)
        if gated is not None:
            return gated

        fields = resolve_fields(rule, context)
        declaration = pick_declaration(declarations, fields) if fields else None
        if declaration is None and not fields and declarations:
            return make_result(
                rule,
                ValidationOutcome.MANUAL_REVIEW,
                "No declaration field mapping is recorded for this requirement.",
            )

        blocked = presence_outcome(
            rule,
            declaration,
            context,
            detected_reason="Required declaration detected.",
        )
        if blocked is not None:
            return blocked

        return make_result(
            rule,
            ValidationOutcome.PASS,
            "Required declaration detected.",
            declaration=declaration,
        )
