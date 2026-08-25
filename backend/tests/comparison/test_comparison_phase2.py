"""Phase 2: Multi-product nutrition comparison scoring & weighting tests.

Verifies:
- Parameter normalization for scoring (min-max relative scoring for higher-is-better and lower-is-better)
- All 10 supported parameters with explicit direction
- Neutral score handling when all available values for a parameter are equal
- Strict missing data rules (NOT_DETECTED, not zero, omitted from weighted score, effective weights re-normalized)
- Priority handling and custom weights (1 to 5) with effective weight normalization
- Deterministic execution across repeated runs
- Validation rejection of invalid weights
- Required test scenarios: lower sugar, higher protein, higher fiber, lower sodium, lower saturated fat, lower calories, mixed priorities, custom weights, equal values, missing sugar, missing protein, multiple missing parameters, different units after normalization, deterministic repeated execution, invalid weights.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.comparison.scoring import score_comparison, PRIORITY_SPEC
from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationStatus,
    NutritionParameter,
    ParameterDirection,
)
from app.schemas.comparison import ComparisonRequest, ComparisonResult


def _build_product(product_id: str, name: str, values_dict: dict) -> dict:
    """Helper to construct a product input payload."""
    encoded = {}
    for param_name, val in values_dict.items():
        param_enum = param_name.upper()
        if val is None:
            encoded[param_enum] = {"status": "NOT_DETECTED"}
        elif isinstance(val, tuple):
            magnitude, unit = val
            encoded[param_enum] = {"value": magnitude, "unit": unit}
        elif isinstance(val, dict):
            encoded[param_enum] = val
    return {"product_id": product_id, "product_name": name, "values": encoded}


def _build_prio(priority: str, weight: int | None = None) -> dict:
    p = {"priority": priority}
    if weight is not None:
        p["weight"] = weight
    return p


def _run_score(products: list[dict], priorities: list[dict]) -> ComparisonResult:
    req = ComparisonRequest.model_validate({"products": products, "priorities": priorities})
    return score_comparison(req)


def _get_product(result: ComparisonResult, product_id: str):
    return next(p for p in result.products if p.product_id == product_id)


def _get_param_score(product_res, parameter: NutritionParameter):
    return next(ps for ps in product_res.parameter_scores if ps.parameter is parameter)


# --- 1. Parameter direction mapping verification -----------------------------


def test_priority_spec_directions() -> None:
    """Verify that lower-is-better and higher-is-better directions are set correctly for all parameters."""
    expected_directions = {
        ComparisonPriority.LOWER_CALORIES: (NutritionParameter.CALORIES, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.LOWER_SUGAR: (NutritionParameter.SUGAR, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.LOWER_ADDED_SUGAR: (NutritionParameter.ADDED_SUGAR, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.HIGHER_PROTEIN: (NutritionParameter.PROTEIN, ParameterDirection.HIGHER_BETTER),
        ComparisonPriority.LOWER_CARBOHYDRATES: (NutritionParameter.CARBOHYDRATES, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.LOWER_FAT: (NutritionParameter.FAT, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.LOWER_SATURATED_FAT: (NutritionParameter.SATURATED_FAT, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.LOWER_TRANS_FAT: (NutritionParameter.TRANS_FAT, ParameterDirection.LOWER_BETTER),
        ComparisonPriority.HIGHER_FIBER: (NutritionParameter.FIBER, ParameterDirection.HIGHER_BETTER),
        ComparisonPriority.LOWER_SODIUM: (NutritionParameter.SODIUM, ParameterDirection.LOWER_BETTER),
    }
    for prio, (param, direction) in expected_directions.items():
        assert PRIORITY_SPEC[prio] == (param, direction)


# --- 2. Single-priority test cases --------------------------------------------


def test_score_lower_sugar() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"sugar": ("15", "g")}), _build_product("B", "Brand B", {"sugar": ("5", "g")})],
        [_build_prio("LOWER_SUGAR")],
    )
    b = _get_product(res, "B")
    a = _get_product(res, "A")
    assert b.rank == 1
    assert b.score == 1.0
    assert a.score == 0.0


def test_score_higher_protein() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"protein": ("2", "g")}), _build_product("B", "Brand B", {"protein": ("10", "g")})],
        [_build_prio("HIGHER_PROTEIN")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0


def test_score_higher_fiber() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"fiber": ("1", "g")}), _build_product("B", "Brand B", {"fiber": ("5", "g")})],
        [_build_prio("HIGHER_FIBER")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0


def test_score_lower_sodium() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"sodium": ("500", "mg")}), _build_product("B", "Brand B", {"sodium": ("100", "mg")})],
        [_build_prio("LOWER_SODIUM")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0


def test_score_lower_saturated_fat() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"saturated_fat": ("6", "g")}), _build_product("B", "Brand B", {"saturated_fat": ("1", "g")})],
        [_build_prio("LOWER_SATURATED_FAT")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0


def test_score_lower_calories() -> None:
    res = _run_score(
        [_build_product("A", "Brand A", {"calories": ("300", "kcal")}), _build_product("B", "Brand B", {"calories": ("150", "kcal")})],
        [_build_prio("LOWER_CALORIES")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0


# --- 3. Mixed priorities & custom weights ------------------------------------


def test_score_mixed_priorities_and_custom_weights() -> None:
    # A: 5g sugar, 4g protein. B: 15g sugar, 12g protein.
    # Lower sugar: A gets 1.0, B gets 0.0.
    # Higher protein: A gets 0.0, B gets 1.0.
    # If sugar weight=3 and protein weight=1:
    # A total = (1.0*3 + 0.0*1)/4 = 0.75
    # B total = (0.0*3 + 1.0*1)/4 = 0.25
    res = _run_score(
        [
            _build_product("A", "Brand A", {"sugar": ("5", "g"), "protein": ("4", "g")}),
            _build_product("B", "Brand B", {"sugar": ("15", "g"), "protein": ("12", "g")}),
        ],
        [_build_prio("LOWER_SUGAR", 3), _build_prio("HIGHER_PROTEIN", 1)],
    )
    a = _get_product(res, "A")
    b = _get_product(res, "B")
    assert a.rank == 1
    assert a.score == pytest.approx(0.75, abs=1e-6)
    assert b.score == pytest.approx(0.25, abs=1e-6)


# --- 4. Equal values ---------------------------------------------------------


def test_score_equal_values_gives_neutral_contribution() -> None:
    res = _run_score(
        [
            _build_product("A", "Brand A", {"sugar": ("10", "g")}),
            _build_product("B", "Brand B", {"sugar": ("10", "g")}),
        ],
        [_build_prio("LOWER_SUGAR")],
    )
    a = _get_product(res, "A")
    b = _get_product(res, "B")
    assert a.score == 0.5
    assert b.score == 0.5
    assert a.outcome is ComparisonOutcome.TIED
    assert b.outcome is ComparisonOutcome.TIED


# --- 5. Missing values (missing sugar, missing protein, multiple missing) ----


def test_missing_sugar_not_treated_as_zero() -> None:
    # A has 10g sugar, B has missing sugar (None).
    # Since only A has a comparable sugar value, sugar is excluded from comparison (fewer than 2 comparable products).
    res = _run_score(
        [
            _build_product("A", "Brand A", {"sugar": ("10", "g")}),
            _build_product("B", "Brand B", {"sugar": None}),
        ],
        [_build_prio("LOWER_SUGAR")],
    )
    assert res.status is ComparisonStatus.INSUFFICIENT_DATA
    b = _get_product(res, "B")
    assert b.score is None
    assert b.outcome is ComparisonOutcome.COULD_NOT_RANK


def test_missing_protein_with_available_sugar() -> None:
    # A: 5g sugar, 10g protein. B: 15g sugar, 2g protein. C: 10g sugar, missing protein.
    # Active: sugar, protein.
    # For C: protein is missing. Effective available weight for C is only sugar (weight=1 -> 1.0).
    # Sugar min=5, max=15. Lower sugar for C (10g) -> (15 - 10) / (15 - 5) = 0.5.
    # So C score is 0.5. C is placed between A (sugar=1.0, protein=1.0 -> 1.0) and B (sugar=0.0, protein=0.0 -> 0.0).
    res = _run_score(
        [
            _build_product("A", "Brand A", {"sugar": ("5", "g"), "protein": ("10", "g")}),
            _build_product("B", "Brand B", {"sugar": ("15", "g"), "protein": ("2", "g")}),
            _build_product("C", "Brand C", {"sugar": ("10", "g"), "protein": None}),
        ],
        [_build_prio("LOWER_SUGAR"), _build_prio("HIGHER_PROTEIN")],
    )
    c = _get_product(res, "C")
    assert c.rank == 2
    assert c.score == pytest.approx(0.5, abs=1e-6)
    assert c.available_parameters == [NutritionParameter.SUGAR]
    assert c.missing_parameters == [NutritionParameter.PROTEIN]


def test_multiple_missing_parameters_re_normalizes_weights() -> None:
    # Priorities: lower sugar (w=2), higher protein (w=1), higher fiber (w=1).
    # Product C has sugar=5g, but missing protein and missing fiber.
    # C's only available parameter is sugar, so sugar's effective weight for C becomes 1.0.
    res = _run_score(
        [
            _build_product("A", "A", {"sugar": ("5", "g"), "protein": ("8", "g"), "fiber": ("6", "g")}),
            _build_product("B", "B", {"sugar": ("15", "g"), "protein": ("2", "g"), "fiber": ("1", "g")}),
            _build_product("C", "C", {"sugar": ("5", "g"), "protein": None, "fiber": None}),
        ],
        [_build_prio("LOWER_SUGAR", 2), _build_prio("HIGHER_PROTEIN", 1), _build_prio("HIGHER_FIBER", 1)],
    )
    c = _get_product(res, "C")
    sugar_ps = _get_param_score(c, NutritionParameter.SUGAR)
    assert sugar_ps.effective_weight == 1.0
    assert c.score == 1.0  # lowest sugar among all 3 products


# --- 6. Different units after normalization -----------------------------------


def test_different_units_after_normalization_in_scoring() -> None:
    # Product A: 0.5 g sodium = 500 mg sodium. Product B: 200 mg sodium.
    # Lower sodium priority -> B (200 mg) wins over A (500 mg).
    res = _run_score(
        [
            _build_product("A", "Brand A", {"sodium": ("0.5", "g")}),
            _build_product("B", "Brand B", {"sodium": ("200", "mg")}),
        ],
        [_build_prio("LOWER_SODIUM")],
    )
    b = _get_product(res, "B")
    assert b.rank == 1
    assert b.score == 1.0
    assert _get_param_score(_get_product(res, "A"), NutritionParameter.SODIUM).canonical_value == Decimal("500")
    assert _get_param_score(b, NutritionParameter.SODIUM).canonical_value == Decimal("200")


# --- 7. Deterministic repeated execution -------------------------------------


def test_deterministic_repeated_execution() -> None:
    products = [
        _build_product("A", "Brand A", {"sugar": ("10", "g"), "protein": ("5", "g")}),
        _build_product("B", "Brand B", {"sugar": ("4", "g"), "protein": ("10", "g")}),
        _build_product("C", "Brand C", {"sugar": ("8", "g"), "protein": ("2", "g")}),
    ]
    priorities = [_build_prio("LOWER_SUGAR", 2), _build_prio("HIGHER_PROTEIN", 3)]

    res1 = _run_score(products, priorities)
    res2 = _run_score(products, priorities)

    assert res1.model_dump() == res2.model_dump()


# --- 8. Invalid weights validation -------------------------------------------


def test_invalid_weights_rejected() -> None:
    for invalid_w in [0, -1, 6, 10]:
        with pytest.raises(ValidationError):
            _run_score(
                [
                    _build_product("A", "A", {"sugar": ("5", "g")}),
                    _build_product("B", "B", {"sugar": ("10", "g")}),
                ],
                [_build_prio("LOWER_SUGAR", invalid_w)],
            )
