"""Phase 9: engine aggregates validator results. No OCR, no database."""

from datetime import date

from app.compliance.engine import NO_APPLICABLE_WARNING, ComplianceEngine
from app.compliance.registry import ValidatorRegistry
from app.compliance.resolver import StaticRuleResolver
from app.compliance.validators.required import RequiredDeclarationValidator
from app.core.enums import ComplianceStatus, RuleStatus, ValidationOutcome, VerificationStatus
from app.schemas.assessment import ComplianceRequest
from app.schemas.legal_rule import LegalRuleRecord
from seeds.legal_rules import load_rule_payloads


def _rule(**overrides) -> LegalRuleRecord:
    base = dict(
        rule_code="TEST-ENG-001",
        rule_name="Fixture requirement",
        description="Not a legal requirement.",
        requirement="Fixture only.",
        category="PACKAGED_COMMODITY",
        validation_type="REQUIRED_DECLARATION",
        source_document="TEST",
        source_reference="Fixture",
        source_version="A",
        effective_from=date(2011, 4, 1),
        effective_to=None,
        rule_status=RuleStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["name"]},
    )
    base.update(overrides)
    return LegalRuleRecord.model_validate(base)


def _engine(rules: list[LegalRuleRecord], registry: ValidatorRegistry | None = None) -> ComplianceEngine:
    return ComplianceEngine(StaticRuleResolver(rules), registry)


def _request(**overrides) -> ComplianceRequest:
    payload = {
        "inspection_date": date(2026, 8, 23),
        "product_category": "HOUSEHOLD_PRODUCT",
        "declarations": {
            "name": {"value": "Bath soap", "confidence": 0.98, "status": "DETECTED"},
            "mrp": {"value": 50, "confidence": 0.98, "status": "DETECTED"},
        },
    }
    payload.update(overrides)
    return ComplianceRequest.model_validate(payload)


def test_all_pass_is_compliant() -> None:
    second = _rule(rule_code="TEST-ENG-002", applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["name"]})
    result = _engine([_rule(), second]).evaluate(_request())

    assert result.status is ComplianceStatus.COMPLIANT
    assert result.passed_count == 2
    assert result.violation_count == 0
    assert result.manual_review_count == 0
    assert result.assessment_confidence is None
    assert "not a legal determination" in result.explanation.lower()


def test_one_potential_non_compliance_wins() -> None:
    mrp = _rule(
        rule_code="TEST-MRP-001",
        validation_type="MRP_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["mrp"]},
    )
    result = _engine([_rule(), mrp]).evaluate(
        _request(declarations={"name": {"value": "Soap", "status": "DETECTED", "confidence": 0.98}, "mrp": {"value": "-50", "status": "DETECTED", "confidence": 0.99}})
    )

    assert result.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert result.violation_count == 1
    assert result.violations[0].rule_code == "TEST-MRP-001"
    assert result.violations[0].source_reference == "Fixture"


def test_manual_review_without_violation() -> None:
    result = _engine([_rule()]).evaluate(
        _request(declarations={"name": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40}})
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0
    assert result.manual_review_count == 1


def test_violation_plus_manual_review_is_potential_non_compliance() -> None:
    mrp = _rule(
        rule_code="TEST-MRP-001",
        validation_type="MRP_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["mrp"]},
    )
    result = _engine([_rule(), mrp]).evaluate(
        _request(
            declarations={
                "name": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40},
                "mrp": {"value": "ABC", "status": "DETECTED", "confidence": 0.99},
            }
        )
    )

    assert result.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert result.manual_review_count == 1
    assert result.violation_count == 1


def test_pass_and_not_applicable_is_compliant() -> None:
    excluded = _rule(
        rule_code="TEST-FOOD-ONLY",
        applicability_condition={"applies_to_categories": ["PACKAGED_FOOD"], "declaration_fields": ["name"]},
    )
    result = _engine([_rule(), excluded]).evaluate(_request())

    assert result.status is ComplianceStatus.COMPLIANT
    assert result.not_applicable_count == 1
    assert result.passed_count == 1
    assert result.not_applicable[0].rule_code == "TEST-FOOD-ONLY"


def test_missing_validator_is_manual_review() -> None:
    rule = _rule(validation_type="READABILITY")
    result = _engine([rule]).evaluate(_request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.manual_review[0].reason == "No validator is currently implemented for this applicable requirement."
    assert result.status is not ComplianceStatus.COMPLIANT
    assert result.status is not ComplianceStatus.POTENTIAL_NON_COMPLIANCE


def test_no_applicable_rules_is_manual_review() -> None:
    result = _engine([]).evaluate(_request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert NO_APPLICABLE_WARNING in result.warnings
    assert result.rule_count == 0


def test_validator_exception_is_manual_review() -> None:
    class BrokenValidator:
        def validate(self, rule, declarations, context):
            raise RuntimeError("unexpected validator failure")

    registry = ValidatorRegistry()
    registry.register("REQUIRED_DECLARATION", BrokenValidator())
    result = _engine([_rule()], registry).evaluate(_request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.manual_review[0].reason == "Validation could not be completed reliably."
    assert result.manual_review[0].rule_code == "TEST-ENG-001"


def test_unverified_rule_is_not_a_violation() -> None:
    draft = _rule(
        rule_code="LM-PC-ORIGIN-001",
        rule_status=RuleStatus.DRAFT,
        verification_status=VerificationStatus.UNVERIFIED,
        applicability_condition={"applies_to_categories": ["IMPORTED_PRODUCT"], "declaration_fields": ["origin"]},
        effective_from=date(2017, 6, 23),
    )
    result = _engine([draft]).evaluate(
        _request(product_category="IMPORTED_PRODUCT", is_imported=True, declarations={"origin": {"value": "India", "status": "DETECTED", "confidence": 0.99}})
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0
    assert result.manual_review_count == 1
    assert any("not verified" in item for item in result.warnings)


def test_historical_version_is_selected() -> None:
    version_a = _rule(source_version="A", effective_from=date(2021, 1, 1), effective_to=date(2024, 12, 31))
    version_b = _rule(source_version="B", effective_from=date(2025, 1, 1), effective_to=None)
    engine = _engine([version_a, version_b])

    older = engine.evaluate(_request(inspection_date=date(2023, 6, 1)))
    newer = engine.evaluate(_request(inspection_date=date(2026, 8, 23)))

    assert older.passed[0].selected_version == "A"
    assert newer.passed[0].selected_version == "B"
    assert older.passed[0].source_version == "A"
    assert newer.passed[0].source_version == "B"


def test_future_rule_is_not_evaluated() -> None:
    future = _rule(rule_code="TEST-FUTURE-001", effective_from=date(2027, 1, 1), source_version="C")
    result = _engine([future]).evaluate(_request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.passed == []
    assert result.violations == []
    assert result.rule_count == 0
    assert any("not evaluated" in item for item in result.warnings)


def test_low_ocr_confidence_stays_manual_review() -> None:
    mrp = _rule(
        rule_code="TEST-MRP-001",
        validation_type="MRP_VALIDATION",
        applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["mrp"]},
    )
    result = _engine([mrp]).evaluate(
        date(2026, 8, 23),
        "HOUSEHOLD_PRODUCT",
        {"label_readable": True},
        {"mrp": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40}},
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert result.violation_count == 0


def test_seed_household_pass_path_and_traceability() -> None:
    rules = [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]
    result = _engine(rules).evaluate(
        _request(
            declarations={
                "manufacturer": {"value": "Acme Packers", "status": "DETECTED", "confidence": 0.98},
                "commodity_name": {"value": "Bath soap", "status": "DETECTED", "confidence": 0.98},
                "net_quantity": {"value": "100 g", "status": "DETECTED", "confidence": 0.98},
                "manufacture_date": {"value": "07/2026", "status": "DETECTED", "confidence": 0.98},
                "mrp": {"value": "₹50", "status": "DETECTED", "confidence": 0.98},
                "consumer_care": {"value": "Acme Care 1800123456", "status": "DETECTED", "confidence": 0.98},
            }
        )
    )

    assert result.status is ComplianceStatus.COMPLIANT
    assert "LM-PC-MRP-001" in [item.rule_code for item in result.passed]
    mrp = next(item for item in result.passed if item.rule_code == "LM-PC-MRP-001")
    assert mrp.source_reference == "Rule 6(1)(e)"
    assert mrp.source_document.startswith("Legal Metrology")
    assert result.assessment_confidence is None


def test_resolver_failure_is_manual_review() -> None:
    class BrokenResolver:
        def resolve(self, context):
            raise RuntimeError("resolver failed")

    result = ComplianceEngine(BrokenResolver()).evaluate(_request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert "could not be completed reliably" in result.warnings[0]


def test_default_registry_is_used_when_omitted() -> None:
    engine = ComplianceEngine(StaticRuleResolver([_rule()]))

    assert isinstance(engine.registry.get("REQUIRED_DECLARATION"), RequiredDeclarationValidator)
