"""Phase 7: pick the in-force version, then classify. No compliance verdicts."""

from datetime import date, datetime, timezone

from app.compliance.dates import as_inspection_date
from app.compliance.selection import evaluate_applicability, select_version_for_date
from app.core.enums import ApplicabilityDecision, RuleStatus, VerificationStatus
from app.schemas.applicability import ProductContext
from app.schemas.legal_rule import LegalRuleRecord
from seeds.legal_rules import load_rule_payloads


def _record(**overrides) -> LegalRuleRecord:
    base = dict(
        rule_code="TEST-VER-001",
        rule_name="Fixture version",
        description="Not a legal requirement.",
        requirement="Fixture only.",
        category="PACKAGED_COMMODITY",
        validation_type="REQUIRED_DECLARATION",
        source_document="TEST",
        source_version="A",
        effective_from=date(2021, 1, 1),
        effective_to=date(2024, 12, 31),
        rule_status=RuleStatus.ACTIVE,
        verification_status=VerificationStatus.VERIFIED,
        applicability_condition={"applies_to_categories": ["*"]},
    )
    base.update(overrides)
    return LegalRuleRecord.model_validate(base)


def test_inspection_date_uses_utc_calendar_day() -> None:
    instant = datetime(2023, 6, 1, 2, 0, tzinfo=timezone.utc)

    assert as_inspection_date(instant) == date(2023, 6, 1)
    assert as_inspection_date(date(2023, 6, 1)) == date(2023, 6, 1)


def test_selects_historical_version_not_the_latest_row() -> None:
    version_a = _record()
    version_b = _record(
        source_version="B",
        effective_from=date(2025, 1, 1),
        effective_to=None,
    )
    versions = [version_a, version_b]

    assert select_version_for_date(versions, date(2023, 6, 1)).source_version == "A"
    assert select_version_for_date(versions, date(2026, 8, 23)).source_version == "B"


def test_evaluate_buckets_version_a_and_b() -> None:
    version_a = _record()
    version_b = _record(source_version="B", effective_from=date(2025, 1, 1), effective_to=None)
    rules = [version_a, version_b]

    in_2023 = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2023, 6, 1), category="HOUSEHOLD_PRODUCT"),
    )
    in_2026 = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2026, 8, 23), category="HOUSEHOLD_PRODUCT"),
    )

    assert in_2023.applicable[0].selected_version == "A"
    assert in_2026.applicable[0].selected_version == "B"
    assert in_2023.codes(ApplicabilityDecision.APPLICABLE) == ["TEST-VER-001"]


def test_seed_food_excludes_manufacturer_rule() -> None:
    rules = [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]
    report = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2026, 8, 23), category="PACKAGED_FOOD"),
    )

    assert "LM-PC-NETQ-001" in report.codes(ApplicabilityDecision.APPLICABLE)
    assert "LM-PC-MRP-001" in report.codes(ApplicabilityDecision.APPLICABLE)
    assert "LM-PC-MFR-001" in report.codes(ApplicabilityDecision.NOT_APPLICABLE)
    assert "LM-PC-DATE-001" in report.codes(ApplicabilityDecision.NOT_APPLICABLE)


def test_imported_product_marks_unverified_origin_rule() -> None:
    rules = [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]
    report = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2026, 8, 23), category="IMPORTED_PRODUCT", is_imported=True),
    )

    assert "LM-PC-ORIGIN-001" in report.codes(ApplicabilityDecision.UNVERIFIED)
    assert "LM-PC-ORIGIN-001" not in report.codes(ApplicabilityDecision.APPLICABLE)


def test_origin_rule_is_future_before_its_window() -> None:
    rules = [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]
    report = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2015, 1, 1), category="IMPORTED_PRODUCT", is_imported=True),
    )

    assert "LM-PC-ORIGIN-001" in report.codes(ApplicabilityDecision.FUTURE)


def test_expired_version_is_not_used_for_later_inspection() -> None:
    expired = _record(effective_from=date(2011, 4, 1), effective_to=date(2020, 12, 31))
    report = evaluate_applicability(
        [expired],
        ProductContext(inspection_date=date(2026, 8, 23), category="OTHER"),
    )

    assert report.codes(ApplicabilityDecision.EXPIRED) == ["TEST-VER-001"]
    assert report.applicable == []


def test_size_rule_applies_only_when_size_is_relevant() -> None:
    rules = [LegalRuleRecord.model_validate(item.model_dump()) for item in load_rule_payloads()]
    without_size = evaluate_applicability(
        rules,
        ProductContext(inspection_date=date(2026, 8, 23), category="HOUSEHOLD_PRODUCT"),
    )
    with_size = evaluate_applicability(
        rules,
        ProductContext(
            inspection_date=date(2026, 8, 23),
            category="HOUSEHOLD_PRODUCT",
            size_is_relevant=True,
        ),
    )

    assert "LM-PC-SIZE-001" in without_size.codes(ApplicabilityDecision.NOT_APPLICABLE)
    assert "LM-PC-SIZE-001" in with_size.codes(ApplicabilityDecision.APPLICABLE)
