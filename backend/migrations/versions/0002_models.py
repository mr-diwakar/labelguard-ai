"""Application tables for inspections, rules and optional intelligence.

Revision ID: 0002_models
Revises: 0001_foundation
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_models"
down_revision: Union[str, Sequence[str], None] = "0001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="INSPECTOR"),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "products",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="OTHER"),
        sa.Column("brand", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_category", "products", ["category"])

    op.create_table(
        "legal_rules",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("rule_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("validation_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="MEDIUM"),
        sa.Column("source_document", sa.String(300), nullable=False),
        sa.Column("source_version", sa.String(64), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("applicability_condition", JSONB, nullable=True),
        sa.Column("is_prototype", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_code", "source_version", "effective_from", name="uq_legal_rules_version"),
    )
    op.create_index("ix_legal_rules_category", "legal_rules", ["category"])
    op.create_index("ix_legal_rules_validation_type", "legal_rules", ["validation_type"])
    op.create_index("ix_legal_rules_code_effective", "legal_rules", ["rule_code", "effective_from"])

    op.create_table(
        "inspections",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="MANUAL_REVIEW"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("rule_reference", sa.String(300), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("image_quality_usable", sa.Boolean(), nullable=True),
        sa.Column("warnings", JSONB, nullable=True),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('COMPLIANT','POTENTIAL_NON_COMPLIANCE','MANUAL_REVIEW')",
            name="ck_inspections_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_inspections_confidence",
        ),
    )
    op.create_index("ix_inspections_product_id", "inspections", ["product_id"])
    op.create_index("ix_inspections_user_id", "inspections", ["user_id"])
    op.create_index("ix_inspections_status", "inspections", ["status"])
    op.create_index("ix_inspections_inspected_at", "inspections", ["inspected_at"])

    op.create_table(
        "product_images",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("inspection_id", UUID, nullable=True),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
    op.create_index("ix_product_images_inspection_id", "product_images", ["inspection_id"])

    op.create_table(
        "declarations",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="OCR"),
        sa.Column("bbox", JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="NOT_DETECTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('DETECTED','NOT_DETECTED','LOW_CONFIDENCE','MANUALLY_VERIFIED')",
            name="ck_declarations_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_declarations_confidence",
        ),
    )
    op.create_index("ix_declarations_inspection_id", "declarations", ["inspection_id"])
    op.create_index("ix_declarations_inspection_field", "declarations", ["inspection_id", "field"])

    op.create_table(
        "nutrition_data",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id"),
    )

    op.create_table(
        "ingredients",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingredients_inspection_id", "ingredients", ["inspection_id"])

    op.create_table(
        "violations",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("rule_id", UUID, nullable=True),
        sa.Column("declaration_id", UUID, nullable=True),
        sa.Column("rule_code", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column(
            "recommended_action",
            sa.Text(),
            nullable=False,
            server_default="Manual verification recommended.",
        ),
        sa.Column("kind", sa.String(32), nullable=False, server_default="POTENTIAL_NON_COMPLIANCE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["legal_rules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["declaration_id"], ["declarations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_violations_inspection_id", "violations", ["inspection_id"])
    op.create_index("ix_violations_rule_id", "violations", ["rule_id"])
    op.create_index("ix_violations_declaration_id", "violations", ["declaration_id"])

    op.create_table(
        "evidence",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("violation_id", UUID, nullable=True),
        sa.Column("image_id", UUID, nullable=True),
        sa.Column("bbox", JSONB, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("warning", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["violation_id"], ["violations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["image_id"], ["product_images.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_inspection_id", "evidence", ["inspection_id"])
    op.create_index("ix_evidence_violation_id", "evidence", ["violation_id"])

    op.create_table(
        "reports",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_inspection_id", "reports", ["inspection_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("evidence")
    op.drop_table("violations")
    op.drop_table("ingredients")
    op.drop_table("nutrition_data")
    op.drop_table("declarations")
    op.drop_table("product_images")
    op.drop_table("inspections")
    op.drop_table("legal_rules")
    op.drop_table("products")
    op.drop_table("users")
