from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection


class NutritionData(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Optional teammate-2 payload. Legal analysis must work when this row is absent."""

    __tablename__ = "nutrition_data"

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    available: Mapped[bool] = mapped_column(nullable=False, default=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)

    inspection: Mapped["Inspection"] = relationship(back_populates="nutrition")
