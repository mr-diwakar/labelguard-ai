"""Phase 10: end-to-end domain tests for the legal pipeline. No OCR, no Postgres."""

from datetime import date

from app.compliance.selection import evaluate_applicability, select_version_for_date
from app.core.enums import ApplicabilityDecision, ComplianceStatus, RuleStatus, VerificationStatus
from app.schemas.applicability import ProductContext
from tests.fixtures.declarations import HOUSEHOLD_PASS, confirmed_absent, not_detected
from tests.fixtures.inspections import engine, request
from tests.fixtures.rules import care_rule, fixture_rule, mrp_rule, net_quantity_rule, seed_rules
from tests.fixtures.validators import broken_required_registry


def test_scenario_all_applicable_requirements_satisfied() -> None:
    result = engine(seed_rules()).evaluate(request(declarations=HOUSEHOLD_PASS))

    assert result.status is ComplianceStatus.COMPLIANT
    assert result.violation_count == 0
    assert result.assessment_confidence is None


def test_scenario_one_supported_violation() -> None:
    declarations = {**HOUSEHOLD_PASS, "mrp": {"value": "-50", "status": "DETECTED", "confidence": 0.99}}
    result = engine(seed_rules()).evaluate(request(declarations=declarations))

    assert result.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert any(item.rule_code == "LM-PC-MRP-001" for item in result.violations)


def test_scenario_uncertain_declaration_is_manual_review() -> None:
    declarations = {**HOUSEHOLD_PASS, "mrp": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40}}
    result = engine(seed_rules()).evaluate(request(declarations=declarations))

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.status is not ComplianceStatus.POTENTIAL_NON_COMPLIANCE


def test_scenario_violation_plus_manual_review() -> None:
    declarations = {
        **HOUSEHOLD_PASS,
        "mrp": {"value": "ABC", "status": "DETECTED", "confidence": 0.99},
        "net_quantity": {"value": None, "status": "NOT_DETECTED", "confidence": 0.35},
    }
    result = engine(seed_rules()).evaluate(request(declarations=declarations))

    assert result.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert result.manual_review_count >= 1
    assert result.violation_count >= 1


def test_scenario_pass_plus_not_applicable_is_compliant() -> None:
    name = fixture_rule()
    food_only = fixture_rule(
        rule_code="TEST-FOOD-ONLY",
        applicability_condition={"applies_to_categories": ["PACKAGED_FOOD"], "declaration_fields": ["name"]},
    )
    result = engine([name, food_only]).evaluate(request())

    assert result.status is ComplianceStatus.COMPLIANT
    assert result.not_applicable_count == 1


def test_mrp_not_detected_low_confidence_is_not_a_violation() -> None:
    result = engine([mrp_rule()]).evaluate(
        request(declarations={"mrp": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40}})
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0


def test_net_quantity_not_detected_low_confidence_is_manual_review() -> None:
    result = engine([net_quantity_rule()]).evaluate(
        request(declarations={"net_quantity": {"value": None, "status": "NOT_DETECTED", "confidence": 0.35}})
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0


def test_consumer_care_not_detected_low_confidence_is_manual_review() -> None:
    result = engine([care_rule()]).evaluate(
        request(declarations={"consumer_care": {"value": None, "status": "NOT_DETECTED", "confidence": 0.45}})
    )

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0


def test_confirmed_absence_differs_from_unknown() -> None:
    rules = [fixture_rule()]
    absent = engine(rules).evaluate(
        request(label_readable=True, declarations={"name": confirmed_absent("name").model_dump()})
    )
    unknown = engine(rules).evaluate(request(declarations={"name": not_detected("name", 0.40).model_dump()}))

    assert absent.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE
    assert unknown.status is ComplianceStatus.MANUAL_REVIEW


def test_historical_and_current_versions() -> None:
    version_a = fixture_rule(source_version="A", effective_from=date(2023, 1, 1), effective_to=date(2024, 12, 31))
    version_b = fixture_rule(source_version="B", effective_from=date(2025, 1, 1), effective_to=None)
    pipeline = engine([version_a, version_b])

    in_2024 = pipeline.evaluate(request(inspection_date=date(2024, 6, 1)))
    in_2026 = pipeline.evaluate(request(inspection_date=date(2026, 6, 1)))

    assert in_2024.passed[0].selected_version == "A"
    assert in_2026.passed[0].selected_version == "B"


def test_future_rule_is_not_evaluated() -> None:
    future = fixture_rule(effective_from=date(2027, 1, 1), source_version="C")
    result = engine([future]).evaluate(request(inspection_date=date(2026, 8, 23)))

    assert result.passed == []
    assert result.violations == []
    assert result.rule_count == 0
    assert any("not evaluated" in item for item in result.warnings)


def test_expired_rule_is_historical_only() -> None:
    expired = fixture_rule(effective_from=date(2023, 1, 1), effective_to=date(2024, 12, 31), source_version="A")
    pipeline = engine([expired])

    current = pipeline.evaluate(request(inspection_date=date(2026, 8, 23)))
    historical = pipeline.evaluate(request(inspection_date=date(2024, 6, 1)))

    assert current.status is ComplianceStatus.MANUAL_REVIEW
    assert current.rule_count == 0
    assert historical.status is ComplianceStatus.COMPLIANT
    assert historical.passed[0].selected_version == "A"


def test_overlapping_versions_are_not_silently_selected() -> None:
    open_a = fixture_rule(source_version="A", effective_from=date(2025, 1, 1), effective_to=None)
    open_b = fixture_rule(source_version="B", effective_from=date(2025, 6, 1), effective_to=None)
    versions = [open_a, open_b]

    assert select_version_for_date(versions, date(2026, 8, 23)) is None

    report = evaluate_applicability(
        versions,
        ProductContext(inspection_date=date(2026, 8, 23), category="HOUSEHOLD_PRODUCT"),
    )
    result = engine(versions).evaluate(request())

    assert report.codes(ApplicabilityDecision.OVERLAP) == ["TEST-FIX-001"]
    assert report.applicable == []
    assert "will not silently pick one" in report.overlaps[0].reason
    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.violation_count == 0
    assert any("Overlapping versions" in item for item in result.warnings)


def test_category_applicability_uses_stored_seed_rules() -> None:
    rules = seed_rules()
    food = evaluate_applicability(rules, ProductContext(inspection_date=date(2026, 8, 23), category="PACKAGED_FOOD"))
    cosmetic = evaluate_applicability(rules, ProductContext(inspection_date=date(2026, 8, 23), category="COSMETIC"))
    imported = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2026, 8, 23), category="IMPORTED_PRODUCT", is_imported=True),
    )
    other = evaluate_applicability(rules, ProductContext(inspection_date=date(2026, 8, 23), category="OTHER"))

    assert "LM-PC-MFR-001" in food.codes(ApplicabilityDecision.NOT_APPLICABLE)
    assert "LM-PC-DATE-001" in food.codes(ApplicabilityDecision.NOT_APPLICABLE)
    assert "LM-PC-MRP-001" in food.codes(ApplicabilityDecision.APPLICABLE)
    assert "LM-PC-DATE-001" in cosmetic.codes(ApplicabilityDecision.NOT_APPLICABLE)
    assert "LM-PC-ORIGIN-001" in imported.codes(ApplicabilityDecision.UNVERIFIED)
    assert "LM-PC-MFR-001" in other.codes(ApplicabilityDecision.APPLICABLE)
    assert "LM-PC-DATE-001" in other.codes(ApplicabilityDecision.APPLICABLE)


def test_unverified_rule_cannot_create_a_violation() -> None:
    draft = fixture_rule(
        rule_status=RuleStatus.DRAFT,
        verification_status=VerificationStatus.UNVERIFIED,
        applicability_condition={"applies_to_categories": ["IMPORTED_PRODUCT"], "declaration_fields": ["origin"]},
    )
    verified = fixture_rule(rule_code="TEST-VERIFIED")
    result = engine([draft, verified]).evaluate(
        request(product_category="IMPORTED_PRODUCT", is_imported=True)
    )

    assert result.violation_count == 0
    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert any(item.rule_code == "TEST-FIX-001" for item in result.manual_review)


def test_missing_validator_is_manual_review() -> None:
    result = engine([fixture_rule(validation_type="READABILITY")]).evaluate(request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert "No validator is currently implemented" in result.manual_review[0].reason


def test_no_applicable_rules_is_manual_review() -> None:
    result = engine([]).evaluate(request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert "No verified applicable rules were available for this inspection." in result.warnings


def test_validator_failure_is_manual_review() -> None:
    result = engine([fixture_rule()], broken_required_registry()).evaluate(request())

    assert result.status is ComplianceStatus.MANUAL_REVIEW
    assert result.manual_review[0].reason == "Validation could not be completed reliably."


def test_aggregation_priority() -> None:
    name = fixture_rule()
    mrp = mrp_rule()

    both_pass = engine([name, mrp]).evaluate(
        request(declarations={"name": {"value": "Soap", "status": "DETECTED", "confidence": 0.98}, "mrp": {"value": "50", "status": "DETECTED", "confidence": 0.98}})
    )
    review = engine([name, mrp]).evaluate(
        request(declarations={"name": {"value": "Soap", "status": "DETECTED", "confidence": 0.98}, "mrp": {"value": None, "status": "NOT_DETECTED", "confidence": 0.40}})
    )
    violation = engine([name, mrp]).evaluate(
        request(declarations={"name": {"value": "Soap", "status": "DETECTED", "confidence": 0.98}, "mrp": {"value": "-1", "status": "DETECTED", "confidence": 0.99}})
    )

    assert both_pass.status is ComplianceStatus.COMPLIANT
    assert review.status is ComplianceStatus.MANUAL_REVIEW
    assert violation.status is ComplianceStatus.POTENTIAL_NON_COMPLIANCE


def test_traceability_fields_survive_aggregation() -> None:
    result = engine(seed_rules()).evaluate(
        request(declarations={**HOUSEHOLD_PASS, "mrp": {"value": "-50", "status": "DETECTED", "confidence": 0.99}})
    )
    item = next(row for row in result.violations if row.rule_code == "LM-PC-MRP-001")

    assert item.rule_id
    assert item.rule_code == "LM-PC-MRP-001"
    assert item.rule_name
    assert item.source_document
    assert item.source_reference == "Rule 6(1)(e)"
    assert item.source_version
    assert item.reason
    assert item.confidence is not None
    assert item.severity
    assert item.recommended_action
    assert item.evidence


def test_same_input_is_deterministic() -> None:
    pipeline = engine(seed_rules())
    first = pipeline.evaluate(request(declarations=HOUSEHOLD_PASS))
    second = pipeline.evaluate(request(declarations=HOUSEHOLD_PASS))

    assert first.model_dump() == second.model_dump()
    assert first.assessment_confidence is None
