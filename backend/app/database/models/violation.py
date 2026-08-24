from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.database.enums import FindingKind, Severity

if TYPE_CHECKING:
    from app.database.models.declaration import Declaration
    from app.database.models.evidence import Evidence
    from app.database.models.inspection import Inspection
    from app.database.models.legal_rule import LegalRule


class Violation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """
    A potential finding stored with the inspection. This is not a legal determination.
    """

    __tablename__ = "violations"

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[UUID | None] = mapped_column(ForeignKey("legal_rules.id", ondelete="RESTRICT"), index=True)
    declaration_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("declarations.id", ondelete="SET NULL"),
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default=Severity.MEDIUM)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Manual verification recommended.",
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=FindingKind.POTENTIAL_NON_COMPLIANCE)

    inspection: Mapped["Inspection"] = relationship(back_populates="violations")
    rule: Mapped["LegalRule | None"] = relationship(back_populates="findings")
    declaration: Mapped["Declaration | None"] = relationship(back_populates="findings")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="violation")
