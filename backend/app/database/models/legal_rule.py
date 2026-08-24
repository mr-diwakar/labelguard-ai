from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.core.enums import RuleStatus, Severity, VerificationStatus

if TYPE_CHECKING:
    from app.database.models.violation import Violation


class LegalRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Versioned rule record. The engine evaluates inspection date against
    effective_from / effective_to. Prototype rows must set is_prototype=True.
    """

    __tablename__ = "legal_rules"
    __table_args__ = (
        UniqueConstraint("rule_code", "source_version", "effective_from", name="uq_legal_rules_version"),
        Index("ix_legal_rules_code_effective", "rule_code", "effective_from"),
    )

    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    validation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default=Severity.UNSPECIFIED)
    source_document: Mapped[str] = mapped_column(String(300), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(120))
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    applicability_condition: Mapped[dict | None] = mapped_column(JSONB)
    rule_status: Mapped[str] = mapped_column(String(16), nullable=False, default=RuleStatus.DRAFT, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
        index=True,
    )
    is_prototype: Mapped[bool] = mapped_column(nullable=False, default=True)

    findings: Mapped[list["Violation"]] = relationship(back_populates="rule")
