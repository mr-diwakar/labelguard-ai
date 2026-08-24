from datetime import date

from app.compliance.engine import ComplianceEngine
from app.compliance.registry import ValidatorRegistry
from app.compliance.resolver import StaticRuleResolver
from app.schemas.assessment import ComplianceRequest
from app.schemas.legal_rule import LegalRuleRecord


def request(**overrides) -> ComplianceRequest:
    payload = {
        "inspection_date": date(2026, 8, 23),
        "product_category": "HOUSEHOLD_PRODUCT",
        "declarations": {"name": {"value": "Bath soap", "status": "DETECTED", "confidence": 0.98}},
    }
    payload.update(overrides)
    return ComplianceRequest.model_validate(payload)


def engine(rules: list[LegalRuleRecord], registry: ValidatorRegistry | None = None) -> ComplianceEngine:
    return ComplianceEngine(StaticRuleResolver(rules), registry)
