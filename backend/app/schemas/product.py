from uuid import UUID

from pydantic import Field

from app.core.enums import ProductCategory
from app.schemas.common import APIModel, MobileModel


class ProductResponse(APIModel):
    id: UUID
    name: str
    category: ProductCategory
    brand: str | None = None


class ProductListResponse(APIModel):
    items: list[ProductResponse] = Field(default_factory=list)


class MobileProductRef(MobileModel):
    """Embedded on inspection cards. category stays optional to match the current UI type."""

    name: str
    category: str | None = None
