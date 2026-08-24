"""Add source reference, rule status and verification status to legal_rules.

Revision ID: 0003_legal_rule_traceability
Revises: 0002_models
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_legal_rule_traceability"
down_revision: Union[str, Sequence[str], None] = "0002_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("legal_rules", sa.Column("source_reference", sa.String(120), nullable=True))
    op.add_column(
        "legal_rules",
        sa.Column("rule_status", sa.String(16), nullable=False, server_default="DRAFT"),
    )
    op.add_column(
        "legal_rules",
        sa.Column("verification_status", sa.String(16), nullable=False, server_default="UNVERIFIED"),
    )
    op.create_index("ix_legal_rules_rule_status", "legal_rules", ["rule_status"])
    op.create_index("ix_legal_rules_verification_status", "legal_rules", ["verification_status"])


def downgrade() -> None:
    op.drop_index("ix_legal_rules_verification_status", table_name="legal_rules")
    op.drop_index("ix_legal_rules_rule_status", table_name="legal_rules")
    op.drop_column("legal_rules", "verification_status")
    op.drop_column("legal_rules", "rule_status")
    op.drop_column("legal_rules", "source_reference")
