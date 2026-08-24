"""Shared request/response fragments."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base for every contract. ORM instances can be adapted later without leaking columns."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MobileModel(APIModel):
    """Public mobile payload. Serialises as camelCase to match the Expo TypeScript types."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )


class HealthResponse(APIModel):
    status: str


class ErrorBody(APIModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorBody


class BoundingBox(APIModel):
    """Normalised 0..1 box used by the evidence overlay on mobile."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
