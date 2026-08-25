"""Phase 13: the deterministic, LLM-free comparison scoring algorithm.

Covers the required scenarios: single-priority wins in both directions, mixed priorities,
equal values, missing parameters (single and multiple), all-equal products, unit
normalisation feeding the score, determinism, weight normalisation, and invalid weights.
The exact formulae are documented in ``app.comparison.scoring``.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.comparison.scoring import PRIORITY_SPEC, score_comparison
from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationStatus,
    NutritionParameter,
)
from app.schemas.comparison import ComparisonRequest, ComparisonResult


def _product(product_id: str, name: str, **values) -> dict:
    """Build a product payload. ``sugar=("10", "g")`` sets a value; ``protein=None`` marks it
    NOT_DETECTED (missing), never zero."""
    encoded: dict[str, dict] = {}
    for key, spec in values.items():
        parameter = key.upper()
        if spec is None:
            encoded[parameter] = {"status": "NOT_DETECTED"}
        else:
            magnitude, unit = spec
            encoded[parameter] = {"value": magnitude, "unit": unit}
    return {"product_id": product_id, "product_name": name, "values": encoded}


def _prio(priority: str, weight: int | None = None) -> dict:
    payload = {"priority": priority}
    if weight is not None:
        payload["weight"] = weight
    return payload


def _score(products: list[dict], priorities: list[dict]) -> ComparisonResult:
    request = ComparisonRequest.model_validate({"products": products, "priorities": priorities})
    return score_comparison(request)


def _by_id(result: ComparisonResult, product_id: str):
    return next(p for p in result.products if p.product_id == product_id)


def _param(product, parameter: NutritionParameter):
    return next(ps for ps in product.parameter_scores if ps.parameter is parameter)


# --- 1-6: single-priority winners in both directions -------------------------


def test_lower_sugar_wins() -> None:
    result = _score(
        [_product("A", "Brand A", sugar=("10", "g")), _product("B", "Brand B", sugar=("5", "g"))],
        [_prio("LOWER_SUGAR")],
    )

    assert result.status is ComparisonStatus.COMPLETED
    assert result.ranking[0].product_id == "B"
    assert _by_id(result, "B").rank == 1
    assert _by_id(result, "B").score == 1.0
    assert _by_id(result, "A").score == 0.0
    assert "Brand B ranks highest" in result.explanation


def test_higher_protein_wins() -> None:
    result = _score(
        [_product("A", "A", protein=("5", "g")), _product("B", "B", protein=("8", "g"))],
        [_prio("HIGHER_PROTEIN")],
    )

    assert result.ranking[0].product_id == "B"
    assert _by_id(result, "B").score == 1.0


def test_higher_fiber_wins() -> None:
    result = _score(
        [_product("A", "A", fiber=("2", "g")), _product("B", "B", fiber=("6", "g"))],
        [_prio("HIGHER_FIBER")],
    )

    assert result.ranking[0].product_id == "B"


def test_lower_sodium_wins() -> None:
    result = _score(
        [_product("A", "A", sodium=("300", "mg")), _product("B", "B", sodium=("120", "mg"))],
        [_prio("LOWER_SODIUM")],
    )

    assert result.ranking[0].product_id == "B"
    assert _param(_by_id(result, "B"), NutritionParameter.SODIUM).unit == "mg"


def test_lower_saturated_fat_wins() -> None:
    result = _score(
        [_product("A", "A", saturated_fat=("4", "g")), _product("B", "B", saturated_fat=("1", "g"))],
        [_prio("LOWER_SATURATED_FAT")],
    )

    assert result.ranking[0].product_id == "B"


def test_lower_calories_wins() -> None:
    result = _score(
        [_product("A", "A", calories=("250", "kcal")), _product("B", "B", calories=("180", "kcal"))],
        [_prio("LOWER_CALORIES")],
    )

    assert result.ranking[0].product_id == "B"
    assert _param(_by_id(result, "B"), NutritionParameter.CALORIES).unit == "kcal"


# --- 7. mixed priorities (weight decides) ------------------------------------


def test_mixed_priorities_respect_weight() -> None:
    # A is best on sugar, B is best on protein; sugar is weighted double, so A wins.
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), protein=("5", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("10", "g")),
        ],
        [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)],
    )

    assert result.ranking[0].product_id == "A"
    assert _by_id(result, "A").score == pytest.approx(2 / 3, abs=1e-6)
    assert _by_id(result, "B").score == pytest.approx(1 / 3, abs=1e-6)


# --- 8. equal values ---------------------------------------------------------


def test_equal_values_tie_deterministically() -> None:
    result = _score(
        [_product("A", "A", sugar=("10", "g")), _product("B", "B", sugar=("10", "g"))],
        [_prio("LOWER_SUGAR")],
    )

    a, b = _by_id(result, "A"), _by_id(result, "B")
    assert a.score == b.score == 0.5  # neutral: neither rewarded nor penalised
    assert a.rank == b.rank == 1
    assert a.outcome is ComparisonOutcome.TIED
    assert "tied" in result.explanation.lower()


# --- 9. one missing parameter ------------------------------------------------


def test_missing_parameter_is_excluded_for_that_product_only() -> None:
    # C has no protein: it is scored on sugar alone, placed between A and B, not sent to last.
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), protein=("8", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("4", "g")),
            _product("C", "C", sugar=("7", "g"), protein=None),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    c = _by_id(result, "C")
    assert NutritionParameter.PROTEIN in result.active_parameters  # A and B still compare it
    assert c.available_parameters == [NutritionParameter.SUGAR]
    assert c.missing_parameters == [NutritionParameter.PROTEIN]
    assert c.coverage == 0.5
    assert c.score == pytest.approx(0.6, abs=1e-6)  # sugar-only, not zero
    assert c.score != 0.0
    assert c.rank == 2

    protein = _param(c, NutritionParameter.PROTEIN)
    assert protein.included is False
    assert protein.status is DeclarationStatus.NOT_DETECTED
    assert protein.normalized_score is None
    assert protein.weighted_contribution is None


# --- 10. multiple missing parameters -----------------------------------------


def test_multiple_missing_parameters() -> None:
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), protein=("8", "g"), fiber=("6", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("4", "g"), fiber=("2", "g")),
            _product("C", "C", sugar=("7", "g"), protein=None, fiber=None),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN"), _prio("HIGHER_FIBER")],
    )

    c = _by_id(result, "C")
    assert set(c.missing_parameters) == {NutritionParameter.PROTEIN, NutritionParameter.FIBER}
    assert c.available_parameters == [NutritionParameter.SUGAR]
    assert c.coverage == pytest.approx(1 / 3, abs=1e-6)
    assert c.score == pytest.approx(0.6, abs=1e-6)
    assert _by_id(result, "A").rank == 1


# --- 11. all products equal --------------------------------------------------


def test_all_products_equal_all_tie() -> None:
    result = _score(
        [
            _product("A", "A", sugar=("10", "g"), protein=("5", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("5", "g")),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    a, b = _by_id(result, "A"), _by_id(result, "B")
    assert a.score == b.score == 0.5
    assert a.rank == b.rank == 1
    assert a.outcome is ComparisonOutcome.TIED
    assert result.status is ComparisonStatus.COMPLETED


# --- 12. different units after normalisation ---------------------------------


def test_different_units_are_normalised_before_scoring() -> None:
    # A declares sodium in grams, B in mg; after normalisation A=200 mg, B=150 mg, so B wins.
    result = _score(
        [_product("A", "A", sodium=("0.2", "g")), _product("B", "B", sodium=("150", "mg"))],
        [_prio("LOWER_SODIUM")],
    )

    assert result.ranking[0].product_id == "B"
    assert _param(_by_id(result, "A"), NutritionParameter.SODIUM).canonical_value == Decimal("200")
    assert _param(_by_id(result, "B"), NutritionParameter.SODIUM).canonical_value == Decimal("150")


# --- 13. determinism ---------------------------------------------------------


def test_repeated_execution_is_identical() -> None:
    products = [
        _product("A", "A", sugar=("5", "g"), protein=("8", "g")),
        _product("B", "B", sugar=("10", "g"), protein=("4", "g")),
    ]
    priorities = [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)]

    first = _score(products, priorities)
    second = _score(products, priorities)

    assert first.model_dump() == second.model_dump()


# --- 14. weight normalisation ------------------------------------------------


def test_effective_weights_sum_to_one_and_contributions_sum_to_score() -> None:
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), protein=("5", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("10", "g")),
        ],
        [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)],
    )

    for product in result.products:
        included = [ps for ps in product.parameter_scores if ps.included]
        assert sum(ps.effective_weight for ps in included) == pytest.approx(1.0, abs=1e-6)
        assert sum(ps.weighted_contribution for ps in included) == pytest.approx(product.score, abs=1e-6)

    a = _by_id(result, "A")
    assert _param(a, NutritionParameter.SUGAR).effective_weight == pytest.approx(2 / 3, abs=1e-6)
    assert _param(a, NutritionParameter.PROTEIN).effective_weight == pytest.approx(1 / 3, abs=1e-6)


def test_missing_parameter_renormalises_remaining_weight_to_one() -> None:
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), protein=("8", "g")),
            _product("B", "B", sugar=("10", "g"), protein=("4", "g")),
            _product("C", "C", sugar=("7", "g"), protein=None),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    sugar = _param(_by_id(result, "C"), NutritionParameter.SUGAR)
    assert sugar.included is True
    assert sugar.effective_weight == 1.0  # sugar is C's only available parameter


# --- 15. invalid weights -----------------------------------------------------


def test_invalid_weights_are_rejected_before_scoring() -> None:
    # Weights are constrained to 1-5 at the contract boundary, so the scorer never sees a bad one.
    for bad in (0, 6, -1):
        with pytest.raises(ValidationError):
            _score(
                [
                    _product("A", "A", sugar=("5", "g")),
                    _product("B", "B", sugar=("10", "g")),
                ],
                [_prio("LOWER_SUGAR", bad)],
            )


# --- supporting guarantees ---------------------------------------------------


def test_priority_spec_covers_every_priority() -> None:
    assert set(PRIORITY_SPEC) == set(ComparisonPriority)


def test_parameter_declared_by_one_product_is_excluded_from_the_comparison() -> None:
    result = _score(
        [
            _product("A", "A", sugar=("5", "g"), fiber=("3", "g")),
            _product("B", "B", sugar=("10", "g"), fiber=None),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_FIBER")],
    )

    excluded = [e.parameter for e in result.excluded_parameters]
    assert NutritionParameter.FIBER in excluded
    assert NutritionParameter.FIBER not in result.active_parameters
    assert result.ranking[0].product_id == "A"  # decided on sugar alone


def test_insufficient_data_when_no_parameter_is_comparable() -> None:
    result = _score(
        [_product("A", "A", protein=("5", "g")), _product("B", "B", protein=("8", "g"))],
        [_prio("LOWER_SUGAR")],  # neither product declares sugar
    )

    assert result.status is ComparisonStatus.INSUFFICIENT_DATA
    assert result.ranking == []
    for product in result.products:
        assert product.outcome is ComparisonOutcome.COULD_NOT_RANK
        assert product.score is None


def test_explanation_never_calls_a_product_healthiest() -> None:
    result = _score(
        [_product("A", "A", sugar=("5", "g")), _product("B", "B", sugar=("10", "g"))],
        [_prio("LOWER_SUGAR")],
    )

    assert "healthiest" not in result.explanation.lower()
    assert "ranks highest" in result.explanation
    assert result.disclaimer  # informational disclaimer always present
