from uuid import UUID

from app.core.enums import ReportStatus
from app.schemas.common import APIModel


class ReportResult(APIModel):
    """Teammate 3 contract. FAILED must leave the inspection saved."""

    inspection_id: UUID
    status: ReportStatus = ReportStatus.PENDING
    storage_path: str | None = None
