"""Empty schema foundation.

Revision ID: 0001_foundation
Revises:
Create Date: 2026-08-23

Tables are added in Phase 4. This revision only proves Alembic can
create its version table against PostgreSQL.
"""

from typing import Sequence, Union

revision: str = "0001_foundation"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
