from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection


class Ingredient(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Optional teammate-2 row. An empty list must not block legal analysis."""

    __tablename__ = "ingredients"

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)

    inspection: Mapped["Inspection"] = relationship(back_populates="ingredients")
