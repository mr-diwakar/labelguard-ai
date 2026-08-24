from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.database.enums import ComplianceStatus

if TYPE_CHECKING:
    from app.database.models.declaration import Declaration
    from app.database.models.evidence import Evidence
    from app.database.models.ingredient import Ingredient
    from app.database.models.nutrition import NutritionData
    from app.database.models.product import Product, ProductImage
    from app.database.models.report import Report
    from app.database.models.user import User
    from app.database.models.violation import Violation


class Inspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inspections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('COMPLIANT','POTENTIAL_NON_COMPLIANCE','MANUAL_REVIEW')",
            name="ck_inspections_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_inspections_confidence",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ComplianceStatus.MANUAL_REVIEW,
        index=True,
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    rule_reference: Mapped[str | None] = mapped_column(String(300))
    is_demo: Mapped[bool] = mapped_column(nullable=False, default=False)
    image_quality_usable: Mapped[bool | None] = mapped_column()
    warnings: Mapped[list | None] = mapped_column(JSONB)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship(back_populates="inspections")
    user: Mapped["User | None"] = relationship(back_populates="inspections")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="inspection")
    declarations: Mapped[list["Declaration"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    nutrition: Mapped["NutritionData | None"] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    violations: Mapped[list["Violation"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
