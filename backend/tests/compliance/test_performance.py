"""Basic local timing. Not an optimization pass."""

import time

from app.core.enums import ComplianceStatus
from tests.fixtures.inspections import engine, request
from tests.fixtures.rules import fixture_rule

TIMINGS: dict[int, float] = {}


def _rules(count: int):
    return [
        fixture_rule(
            rule_code=f"TEST-PERF-{index:03d}",
            applicability_condition={"applies_to_categories": ["*"], "declaration_fields": ["name"]},
        )
        for index in range(count)
    ]


def _time_evaluate(count: int) -> float:
    pipeline = engine(_rules(count))
    payload = request()
    started = time.perf_counter()
    result = pipeline.evaluate(payload)
    elapsed = time.perf_counter() - started
    TIMINGS[count] = elapsed
    assert result.status is ComplianceStatus.COMPLIANT
    assert result.passed_count == count
    return elapsed


def test_engine_stays_local_and_fast_for_10_50_100_rules() -> None:
    for count in (10, 50, 100):
        elapsed = _time_evaluate(count)
        assert elapsed < 2.0, f"{count} rules took {elapsed:.3f}s"
