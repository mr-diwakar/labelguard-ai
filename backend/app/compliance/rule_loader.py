"""Read-side helper for later engine phases. No FastAPI imports."""

from datetime import date

from sqlalchemy.orm import Session

from app.compliance.repository import LegalRuleRepository
from app.compliance.selection import evaluate_applicability
from app.database.models.legal_rule import LegalRule
from app.schemas.applicability import ApplicabilityReport, ProductContext


class RuleLoader:
    def __init__(self, session: Session) -> None:
        self.repository = LegalRuleRepository(session)

    def load_active_rules(self, on_date: date | None = None) -> list[LegalRule]:
        return self.repository.get_active_rules(on_date=on_date)

    def load_rules_by_category(self, category: str, on_date: date | None = None) -> list[LegalRule]:
        return self.repository.get_rules_for_category(category, on_date=on_date)

    def load_rules_by_date(self, on_date: date) -> list[LegalRule]:
        return self.repository.get_rules_for_date(on_date)

    def load_authoritative_rules(self, on_date: date | None = None, category: str | None = None) -> list[LegalRule]:
        return self.repository.get_authoritative_rules(on_date=on_date, category=category)

    def load_by_code(self, rule_code: str, on_date: date | None = None) -> LegalRule | None:
        return self.repository.get_rule_by_code(rule_code, on_date=on_date)

    def select_for_inspection(self, context: ProductContext) -> ApplicabilityReport:
        """
        Version-aware selection for one inspection.

        Pass the inspection date. Do not omit it and rely on 'the latest row'.
        """
        records = [self.repository.to_record(row) for row in self.repository.list_all()]
        return evaluate_applicability(records, context)

    def resolve(self, context: ProductContext) -> ApplicabilityReport:
        """RuleResolver protocol alias. The engine calls this, not the repository."""
        return self.select_for_inspection(context)
