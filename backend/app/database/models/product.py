from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.enums import ProductCategory

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default=ProductCategory.OTHER, index=True)
    brand: Mapped[str | None] = mapped_column(String(200))

    images: Mapped[list["ProductImage"]] = relationship(back_populates="product")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="product")


class ProductImage(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Stored file metadata. storage_path is generated; never trust original_filename as a path."""

    __tablename__ = "product_images"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inspections.id", ondelete="SET NULL"),
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")
    inspection: Mapped["Inspection | None"] = relationship(back_populates="images")
