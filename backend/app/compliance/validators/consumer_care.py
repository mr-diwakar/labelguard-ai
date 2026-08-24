import re
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

_ALNUM = re.compile(r"[A-Za-z0-9]")
_ONLY_NOISE = re.compile(r"^[\W_]+$")


class ConsumerCareValidator:
    """
    Presence and obvious-malformation check only.

    Rule 6(2) asks for name, address, telephone and e-mail if available.
    This validator does not decide whether a particular phone or e-mail format
    is legally sufficient.
    """

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
            detected_reason="Consumer-care information could not be reliably verified from available evidence.",
        )
        if blocked is not None:
            return blocked

        text = (declaration.value or "").strip()
        if _ONLY_NOISE.fullmatch(text) or not _ALNUM.search(text):
            return make_result(
                rule,
                ValidationOutcome.POTENTIAL_NON_COMPLIANCE,
                "The consumer-care value is present but contains no usable characters.",
                declaration=declaration,
            )

        return make_result(
            rule,
            ValidationOutcome.PASS,
            "Consumer-care information was detected.",
            declaration=declaration,
        )
