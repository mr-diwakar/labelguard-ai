from pydantic import Field

from app.schemas.common import APIModel


class IngredientItem(APIModel):
    """Teammate 2 contract. An empty list is a valid result.

    Phase 11 added the optional fields below for the extraction layer (normalised name,
    on-label order, confidence, and a pointer back to the OCR region). They all default
    to None/absent, so existing {"name": ..., "raw_text": ...} payloads validate
    unchanged and no consumer of the original two fields is affected.
    """

    name: str
    raw_text: str | None = None
    normalized_name: str | None = None
    position: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_reference: str | None = None
