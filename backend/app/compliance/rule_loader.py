"""Read-side helper for later engine phases. No FastAPI imports."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.compliance.repository import LegalRuleRepository
from app.compliance.resolver import StaticRuleResolver
from app.compliance.selection import evaluate_applicability
from app.core.logging_config import get_logger
from app.database.models.legal_rule import LegalRule
from app.schemas.applicability import ApplicabilityReport, ProductContext
from app.schemas.legal_rule import LegalRuleRecord

logger = get_logger("compliance")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROTOTYPE_RULES_PATH = _REPO_ROOT / "legal-rules" / "2011" / "rules.json"


def load_prototype_rule_records(path: Path | None = None) -> list[LegalRuleRecord]:
    """Load the committed 2011 prototype rules. Used when PostgreSQL is unreachable."""
    document = json.loads((path or _PROTOTYPE_RULES_PATH).read_text(encoding="utf-8"))
    return [LegalRuleRecord.model_validate(item) for item in document["rules"]]


class PrototypeFallbackResolver:
    """DB-backed resolver that falls back to the prototype JSON, never to a fake verdict."""

    def __init__(self, primary: RuleLoader) -> None:
        self.primary = primary
        self._fallback: StaticRuleResolver | None = None

    @property
    def repository(self) -> LegalRuleRepository:
        return self.primary.repository

    def resolve(self, context: ProductContext) -> ApplicabilityReport:
        try:
            return self.primary.resolve(context)
        except Exception as exc:
            logger.warning(
                "stage=rule_loader event=db_unavailable fallback=prototype_json error=%s",
                type(exc).__name__,
            )
            logger.debug("stage=rule_loader fallback_detail", exc_info=exc)
            if self._fallback is None:
                self._fallback = StaticRuleResolver(load_prototype_rule_records())
            return self._fallback.resolve(context)


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
