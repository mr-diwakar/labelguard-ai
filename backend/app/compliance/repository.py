"""Persistence for versioned legal rules. Does not evaluate compliance."""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.compliance.applicability import is_authoritative, is_effective_on, matches_category
from app.core.enums import RuleStatus
from app.database.models.legal_rule import LegalRule
from app.schemas.legal_rule import LegalRuleCreate, LegalRuleRecord


class LegalRuleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_rule(self, payload: LegalRuleCreate) -> LegalRule:
        existing = self._version_query(payload.rule_code, payload.source_version, payload.effective_from).scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                f"A version of {payload.rule_code} already exists for {payload.source_version} / {payload.effective_from}."
            )

        rule = LegalRule(**payload.model_dump())
        self.session.add(rule)
        self.session.flush()
        return rule

    def upsert_rule(self, payload: LegalRuleCreate) -> LegalRule:
        existing = self._version_query(payload.rule_code, payload.source_version, payload.effective_from).scalar_one_or_none()
        values = payload.model_dump()

        if existing is None:
            rule = LegalRule(**values)
            self.session.add(rule)
            self.session.flush()
            return rule

        for key, value in values.items():
            setattr(existing, key, value)

        self.session.flush()
        return existing

    def get_rule_by_code(self, rule_code: str, on_date: date | None = None) -> LegalRule | None:
        rows = list(self.session.scalars(select(LegalRule).where(LegalRule.rule_code == rule_code)).all())
        if on_date is None:
            current = [row for row in rows if row.effective_to is None]
            return current[0] if current else (rows[-1] if rows else None)

        matching = [row for row in rows if is_effective_on(row.effective_from, row.effective_to, on_date)]
        return matching[-1] if matching else None

    def get_active_rules(
        self,
        *,
        on_date: date | None = None,
        category: str | None = None,
        verified_only: bool = False,
    ) -> list[LegalRule]:
        statement: Select[tuple[LegalRule]] = select(LegalRule).where(LegalRule.rule_status == RuleStatus.ACTIVE)
        rows = list(self.session.scalars(statement).all())
        target = on_date or date.today()

        selected: list[LegalRule] = []
        for row in rows:
            if not is_effective_on(row.effective_from, row.effective_to, target):
                continue
            if not matches_category(row.category, row.applicability_condition, category):
                continue
            if verified_only and not is_authoritative(row.rule_status, row.verification_status):
                continue
            selected.append(row)

        return selected

    def get_rules_for_category(self, category: str, on_date: date | None = None) -> list[LegalRule]:
        return self.get_active_rules(on_date=on_date, category=category)

    def get_rules_for_date(self, on_date: date, category: str | None = None) -> list[LegalRule]:
        return self.get_active_rules(on_date=on_date, category=category)

    def list_all(self) -> list[LegalRule]:
        return list(self.session.scalars(select(LegalRule)).all())

    def get_authoritative_rules(self, on_date: date | None = None, category: str | None = None) -> list[LegalRule]:
        """Only ACTIVE + VERIFIED rows. Unverified drafts never become production rules here."""
        return self.get_active_rules(on_date=on_date, category=category, verified_only=True)

    def update_rule_version(self, rule_code: str, amendment_date: date, payload: LegalRuleCreate) -> LegalRule:
        """
        Closes the open version on the day before the amendment and inserts a new row.
        The previous row is never deleted.
        """
        current = self.get_rule_by_code(rule_code)
        if current is not None and current.effective_to is None:
            current.effective_to = amendment_date - timedelta(days=1)
            if current.rule_status == RuleStatus.ACTIVE:
                current.rule_status = RuleStatus.RETIRED

        payload_data = payload.model_dump()
        payload_data["rule_code"] = rule_code
        payload_data["effective_from"] = amendment_date
        return self.create_rule(LegalRuleCreate.model_validate(payload_data))

    def count_by_code(self, rule_code: str) -> int:
        return len(list(self.session.scalars(select(LegalRule).where(LegalRule.rule_code == rule_code)).all()))

    def get(self, rule_id: UUID) -> LegalRule | None:
        return self.session.get(LegalRule, rule_id)

    def to_record(self, rule: LegalRule) -> LegalRuleRecord:
        return LegalRuleRecord.model_validate(rule)

    def _version_query(self, rule_code: str, source_version: str, effective_from: date):
        return self.session.scalars(
            select(LegalRule).where(
                LegalRule.rule_code == rule_code,
                LegalRule.source_version == source_version,
                LegalRule.effective_from == effective_from,
            )
        )
