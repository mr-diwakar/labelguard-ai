from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.database.enums import EvidenceStatus

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection
    from app.database.models.product import ProductImage
    from app.database.models.violation import Violation


class Evidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Attached to an inspection and optionally to one finding. Failure must not roll back the inspection."""

    __tablename__ = "evidence"

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    violation_id: Mapped[UUID | None] = mapped_column(ForeignKey("violations.id", ondelete="SET NULL"), index=True)
    image_id: Mapped[UUID | None] = mapped_column(ForeignKey("product_images.id", ondelete="SET NULL"))
    bbox: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EvidenceStatus.UNAVAILABLE)
    warning: Mapped[str | None] = mapped_column(String(300))

    inspection: Mapped["Inspection"] = relationship(back_populates="evidence")
    violation: Mapped["Violation | None"] = relationship(back_populates="evidence")
    image: Mapped["ProductImage | None"] = relationship()
