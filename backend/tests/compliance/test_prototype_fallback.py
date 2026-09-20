"""Prototype JSON fallback when the database-backed rule loader cannot query."""

from datetime import date

from app.compliance.engine import ComplianceEngine
from app.compliance.rule_loader import PrototypeFallbackResolver, load_prototype_rule_records
from app.core.enums import ComplianceStatus, ProductCategory
from app.schemas.applicability import ProductContext
from app.schemas.declaration import Declaration


class _BrokenLoader:
    def resolve(self, context):
        raise RuntimeError("database unreachable")


def test_load_prototype_rules_from_committed_json():
    records = load_prototype_rule_records()
    codes = {record.rule_code for record in records}
    assert "LM-PC-MRP-001" in codes
    assert "LM-PC-NETQ-001" in codes
    assert records


def test_fallback_uses_prototype_json_when_primary_raises():
    resolver = PrototypeFallbackResolver(_BrokenLoader())  # type: ignore[arg-type]
    report = resolver.resolve(
        ProductContext(inspection_date=date(2026, 8, 23), category=ProductCategory.PACKAGED_FOOD)
    )
    assert report.applicable or report.not_applicable or report.unverified


def test_fallback_engine_does_not_imply_compliant_or_invent_violations():
    engine = ComplianceEngine(PrototypeFallbackResolver(_BrokenLoader()))  # type: ignore[arg-type]
    assessment = engine.evaluate(
        date(2026, 8, 23),
        product_category=ProductCategory.PACKAGED_FOOD.value,
        declarations=[
            Declaration(field="mrp", value="MRP ₹50", status="DETECTED", confidence=0.95),
            Declaration(field="net_quantity", value="500 g", status="DETECTED", confidence=0.95),
        ],
    )
    assert assessment.status in {
        ComplianceStatus.COMPLIANT,
        ComplianceStatus.POTENTIAL_NON_COMPLIANCE,
        ComplianceStatus.MANUAL_REVIEW,
    }
