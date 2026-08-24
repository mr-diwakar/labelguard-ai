from uuid import UUID

from pydantic import Field

from app.core.enums import EvidenceStatus
from app.schemas.common import APIModel, BoundingBox


class EvidenceItem(APIModel):
    """Teammate 3 contract. A failed generation becomes a warning, not a failed inspection."""

    id: UUID | None = None
    status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    bbox: BoundingBox | None = None
    notes: str | None = None
    warning: str | None = None
    violation_id: UUID | None = None


class EvidenceUnavailable(APIModel):
    warning: str = "Evidence generation unavailable. Manual verification recommended."
    items: list[EvidenceItem] = Field(default_factory=list)
