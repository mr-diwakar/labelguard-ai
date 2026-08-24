from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.enums import ReportStatus

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """PDF artefact. A FAILED report must leave the inspection row intact."""

    __tablename__ = "reports"

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReportStatus.PENDING)

    inspection: Mapped["Inspection"] = relationship(back_populates="reports")
