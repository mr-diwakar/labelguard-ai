"""Phase 4: mapped tables, keys and statuses exist without talking to PostgreSQL."""

from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect
from sqlalchemy.schema import CreateTable

from app.database.base import Base
from app.database.enums import ComplianceStatus, DeclarationStatus
from app.database.models import APPLICATION_TABLES


def test_all_application_tables_are_mapped() -> None:
    assert tuple(sorted(Base.metadata.tables)) == tuple(sorted(APPLICATION_TABLES))


def test_declaration_status_does_not_include_missing() -> None:
    assert "MISSING" not in DeclarationStatus.__members__
    assert set(DeclarationStatus) == {
        DeclarationStatus.DETECTED,
        DeclarationStatus.NOT_DETECTED,
        DeclarationStatus.LOW_CONFIDENCE,
        DeclarationStatus.MANUALLY_VERIFIED,
    }


def test_compliance_status_matches_product_contract() -> None:
    assert set(ComplianceStatus) == {
        ComplianceStatus.COMPLIANT,
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        ComplianceStatus.MANUAL_REVIEW,
    }


def test_inspection_foreign_keys() -> None:
    inspections = Base.metadata.tables["inspections"]

    assert next(iter(inspections.c.product_id.foreign_keys)).column.table.name == "products"
    assert next(iter(inspections.c.user_id.foreign_keys)).column.table.name == "users"


def test_inspection_children_cascade_from_inspection() -> None:
    declarations = Base.metadata.tables["declarations"]
    fk = next(iter(declarations.c.inspection_id.foreign_keys))

    assert fk.ondelete == "CASCADE"


def test_product_cannot_be_deleted_while_inspections_exist() -> None:
    inspections = Base.metadata.tables["inspections"]
    fk = next(iter(inspections.c.product_id.foreign_keys))

    assert fk.ondelete == "RESTRICT"


def test_timestamps_are_timezone_aware() -> None:
    inspections = Base.metadata.tables["inspections"]

    assert inspections.c.created_at.type.timezone is True
    assert inspections.c.updated_at.type.timezone is True
    assert inspections.c.inspected_at.type.timezone is True


def test_schema_compiles_for_postgres() -> None:
    pg = postgresql_dialect()

    for name in APPLICATION_TABLES:
        sql = str(CreateTable(Base.metadata.tables[name]).compile(dialect=pg))
        assert f"create table {name}" in sql.lower().replace('"', "")
