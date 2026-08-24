from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.enums import UserRole

if TYPE_CHECKING:
    from app.database.models.inspection import Inspection


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Account placeholder. Authentication arrives in a later phase."""

    __tablename__ = "users"

    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.INSPECTOR)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)

    inspections: Mapped[list["Inspection"]] = relationship(back_populates="user")
