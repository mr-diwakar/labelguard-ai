from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.database.enums import DeclarationSource, DeclarationStatus

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection
    from app.database.models.violation import Violation


class Declaration(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "declarations"
    __table_args__ = (
        Index("ix_declarations_inspection_field", "inspection_id", "field"),
        CheckConstraint(
            "status IN ('DETECTED','NOT_DETECTED','LOW_CONFIDENCE','MANUALLY_VERIFIED')",
            name="ck_declarations_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_declarations_confidence",
        ),
    )

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default=DeclarationSource.OCR)
    bbox: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DeclarationStatus.NOT_DETECTED)

    inspection: Mapped["Inspection"] = relationship(back_populates="declarations")
    findings: Mapped[list["Violation"]] = relationship(back_populates="declaration")
