"""Rule resolution adapter. The engine never loads rows itself."""

from collections.abc import Sequence
from typing import Protocol

from app.compliance.selection import evaluate_applicability
from app.schemas.applicability import ApplicabilityReport, ProductContext
from app.schemas.legal_rule import LegalRuleRecord


class RuleResolver(Protocol):
    def resolve(self, context: ProductContext) -> ApplicabilityReport: ...


class StaticRuleResolver:
    """In-memory resolver for tests and later service wiring. No database import."""

    def __init__(self, rules: Sequence[LegalRuleRecord]) -> None:
        self._rules = list(rules)

    def resolve(self, context: ProductContext) -> ApplicabilityReport:
        return evaluate_applicability(self._rules, context)
