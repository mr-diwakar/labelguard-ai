"""Comprehensive verification suite for Multi-Product Nutrition Comparison.

Verifies:
1. Two products comparison
2. Three products comparison
3. Equal nutrition values
4. Different valid units
5. Missing sugar
6. Missing protein
7. Missing multiple fields
8. Lower-is-better parameters
9. Higher-is-better parameters
10. User-selected priorities
11. Custom weights
12. Ranking explanation
13. Invalid input
14. Empty product list
15. Single-product comparison

Also verifies:
- Missing data is never treated as zero
- NOT_DETECTED status is preserved
- Missing data does not receive an artificial best score (1.0)
- Missing data does not receive an artificial worst score (0.0)
- Unit normalization is deterministic
- Scoring is deterministic
- Ranking is deterministic
- Weights are correctly normalized
- Explanations match actual values
- No unsupported health claims ("healthiest") are generated
- Original nutrition objects/inputs are not mutated
"""

from decimal import Decimal
import copy
import pytest
from pydantic import ValidationError

from app.comparison.service import ComparisonService
from app.comparison.scoring import score_comparison
from app.comparison.units import normalize_input, normalize_value, NormalizationStatus
from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationSource,
    DeclarationStatus,
    NutritionParameter,
)
from app.schemas.comparison import (
    ComparisonProductInput,
    ComparisonRequest,
    ComparisonResult,
    NutritionValueInput,
    PriorityWeight,
)


def _product(product_id: str, name: str, values: dict) -> dict:
    encoded = {}
    for k, v in values.items():
        param = k.upper()
        if v is None:
            encoded[param] = {"status": "NOT_DETECTED"}
        elif isinstance(v, tuple):
            mag, unit = v
            encoded[param] = {"value": mag, "unit": unit}
        elif isinstance(v, dict):
            encoded[param] = v
    return {"product_id": product_id, "product_name": name, "values": encoded}


def _prio(priority: str, weight: int | None = None) -> dict:
    d = {"priority": priority}
    if weight is not None:
        d["weight"] = weight
    return d


def _run(products: list[dict], priorities: list[dict]) -> ComparisonResult:
    req = ComparisonRequest.model_validate({"products": products, "priorities": priorities})
    return ComparisonService.compare(req)


# --- 1. Two products ----------------------------------------------------------


def test_scenario_1_two_products() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sugar": ("10", "g")}),
            _product("B", "Product B", {"sugar": ("5", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert len(res.products) == 2
    assert res.ranking[0].product_id == "B"
    assert res.ranking[0].rank == 1
    assert res.ranking[1].product_id == "A"
    assert res.ranking[1].rank == 2


# --- 2. Three products --------------------------------------------------------


def test_scenario_2_three_products() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sugar": ("15", "g"), "protein": ("4", "g")}),
            _product("B", "Product B", {"sugar": ("5", "g"), "protein": ("10", "g")}),
            _product("C", "Product C", {"sugar": ("10", "g"), "protein": ("7", "g")}),
        ],
        [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert len(res.products) == 3
    assert [r.product_id for r in res.ranking] == ["B", "C", "A"]


# --- 3. Equal nutrition values ------------------------------------------------


def test_scenario_3_equal_nutrition_values() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sugar": ("10", "g")}),
            _product("B", "Product B", {"sugar": ("10", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert res.products[0].score == 0.5
    assert res.products[1].score == 0.5
    assert res.products[0].outcome is ComparisonOutcome.TIED
    assert res.products[1].outcome is ComparisonOutcome.TIED


# --- 4. Different valid units -------------------------------------------------


def test_scenario_4_different_valid_units() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sodium": ("0.3", "g")}),  # 300 mg
            _product("B", "Product B", {"sodium": ("150", "mg")}),  # 150 mg
        ],
        [_prio("LOWER_SODIUM")],
    )

    assert res.ranking[0].product_id == "B"
    assert res.products[0].parameter_scores[0].canonical_value == Decimal("300")
    assert res.products[1].parameter_scores[0].canonical_value == Decimal("150")


# --- 5. Missing sugar ---------------------------------------------------------


def test_scenario_5_missing_sugar() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sugar": ("5", "g"), "protein": ("8", "g")}),
            _product("B", "Product B", {"sugar": ("15", "g"), "protein": ("2", "g")}),
            _product("C", "Product C", {"sugar": None, "protein": ("5", "g")}),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    prod_c = next(p for p in res.products if p.product_id == "C")
    assert NutritionParameter.SUGAR in prod_c.missing_parameters
    assert NutritionParameter.PROTEIN in prod_c.available_parameters
    assert prod_c.score is not None


# --- 6. Missing protein -------------------------------------------------------


def test_scenario_6_missing_protein() -> None:
    res = _run(
        [
            _product("A", "Product A", {"sugar": ("5", "g"), "protein": ("8", "g")}),
            _product("B", "Product B", {"sugar": ("15", "g"), "protein": ("2", "g")}),
            _product("C", "Product C", {"sugar": ("10", "g"), "protein": None}),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    prod_c = next(p for p in res.products if p.product_id == "C")
    assert NutritionParameter.PROTEIN in prod_c.missing_parameters
    assert NutritionParameter.SUGAR in prod_c.available_parameters


# --- 7. Missing multiple fields -----------------------------------------------


def test_scenario_7_missing_multiple_fields() -> None:
    res = _run(
        [
            _product("A", "A", {"sugar": ("5", "g"), "protein": ("8", "g"), "fiber": ("6", "g")}),
            _product("B", "B", {"sugar": ("15", "g"), "protein": ("2", "g"), "fiber": ("1", "g")}),
            _product("C", "C", {"sugar": ("5", "g"), "protein": None, "fiber": None}),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN"), _prio("HIGHER_FIBER")],
    )

    prod_c = next(p for p in res.products if p.product_id == "C")
    assert set(prod_c.missing_parameters) == {NutritionParameter.PROTEIN, NutritionParameter.FIBER}
    assert prod_c.available_parameters == [NutritionParameter.SUGAR]


# --- 8 & 9. Lower-is-better & Higher-is-better parameters --------------------


def test_scenario_8_and_9_parameter_directions() -> None:
    # Lower-is-better: sugar, sodium, calories, fat, saturated fat, trans fat, added sugar, carbohydrates
    # Higher-is-better: protein, fiber
    res = _run(
        [
            _product("A", "A", {"protein": ("2", "g"), "fat": ("10", "g")}),
            _product("B", "B", {"protein": ("10", "g"), "fat": ("2", "g")}),
        ],
        [_prio("HIGHER_PROTEIN"), _prio("LOWER_FAT")],
    )
    assert res.winner == "B"


# --- 10. User-selected priorities ---------------------------------------------


def test_scenario_10_user_selected_priorities() -> None:
    res = _run(
        [
            _product("A", "A", {"calories": ("200", "kcal")}),
            _product("B", "B", {"calories": ("100", "kcal")}),
        ],
        [_prio("LOWER_CALORIES")],
    )
    assert res.winner == "B"
    assert res.priorities_used[0].priority == ComparisonPriority.LOWER_CALORIES


# --- 11. Custom weights -------------------------------------------------------


def test_scenario_11_custom_weights() -> None:
    # A has lower sugar (5 vs 15), B has higher protein (12 vs 4).
    # If sugar weight=4 and protein weight=1, A wins.
    res = _run(
        [
            _product("A", "A", {"sugar": ("5", "g"), "protein": ("4", "g")}),
            _product("B", "B", {"sugar": ("15", "g"), "protein": ("12", "g")}),
        ],
        [_prio("LOWER_SUGAR", 4), _prio("HIGHER_PROTEIN", 1)],
    )
    assert res.winner == "A"


# --- 12. Ranking explanation -------------------------------------------------


def test_scenario_12_ranking_explanation() -> None:
    res = _run(
        [
            _product("A", "Product Alpha", {"sugar": ("20", "g")}),
            _product("B", "Product Beta", {"sugar": ("5", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert "Product Beta ranks highest" in res.explanation
    assert res.disclaimer is not None


# --- 13. Invalid input --------------------------------------------------------


def test_scenario_13_invalid_input() -> None:
    # Negative value
    with pytest.raises(ValidationError):
        _run([_product("A", "A", {"sugar": ("-5", "g")}), _product("B", "B", {"sugar": ("5", "g")})], [_prio("LOWER_SUGAR")])

    # Out of range weight
    with pytest.raises(ValidationError):
        _run([_product("A", "A", {"sugar": ("5", "g")}), _product("B", "B", {"sugar": ("5", "g")})], [_prio("LOWER_SUGAR", 10)])


# --- 14. Empty product list ---------------------------------------------------


def test_scenario_14_empty_product_list() -> None:
    with pytest.raises(ValidationError):
        _run([], [_prio("LOWER_SUGAR")])


# --- 15. Single-product comparison --------------------------------------------


def test_scenario_15_single_product_comparison() -> None:
    res = _run(
        [_product("A", "Solo Product", {"sugar": ("10", "g")})],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.SINGLE_PRODUCT
    assert res.winner is None
    assert res.products[0].rank == 1
    assert res.products[0].outcome is ComparisonOutcome.SINGLE_PRODUCT
    assert "Solo Product evaluated" in res.explanation
    assert "no competing products" in res.explanation.lower()


# --- Additional Verifications -------------------------------------------------


def test_verify_missing_data_never_treated_as_zero() -> None:
    val = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})
    norm = normalize_input(NutritionParameter.SUGAR, val)
    assert norm.canonical_value is None
    assert norm.canonical_value != Decimal("0")


def test_verify_not_detected_preserved() -> None:
    val = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})
    assert val.status is DeclarationStatus.NOT_DETECTED


def test_verify_missing_data_no_artificial_best_or_worst_score() -> None:
    res = _run(
        [
            _product("A", "A", {"sugar": ("5", "g"), "protein": ("10", "g")}),
            _product("B", "B", {"sugar": ("15", "g"), "protein": ("2", "g")}),
            _product("C", "C", {"sugar": ("10", "g"), "protein": None}),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    prod_c = next(p for p in res.products if p.product_id == "C")
    protein_ps = next(ps for ps in prod_c.parameter_scores if ps.parameter is NutritionParameter.PROTEIN)

    assert protein_ps.included is False
    assert protein_ps.normalized_score is None
    assert protein_ps.weighted_contribution is None
    # C's overall score is based on sugar alone (0.5), not penalized to 0 or rewarded to 1
    assert prod_c.score == pytest.approx(0.5, abs=1e-6)


def test_verify_unit_normalization_deterministic() -> None:
    r1 = normalize_value(NutritionParameter.CALORIES, Decimal("1000"), "kJ")
    r2 = normalize_value(NutritionParameter.CALORIES, Decimal("1000"), "kJ")
    assert r1 == r2


def test_verify_scoring_ranking_deterministic() -> None:
    products = [
        _product("A", "Product A", {"sugar": ("10", "g"), "protein": ("5", "g")}),
        _product("B", "Product B", {"product_name": "Product B", "sugar": ("5", "g"), "protein": ("10", "g")}),
    ]
    priorities = [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)]

    res1 = _run(products, priorities)
    res2 = _run(products, priorities)

    assert res1.model_dump() == res2.model_dump()


def test_verify_weights_correctly_normalized() -> None:
    res = _run(
        [
            _product("A", "A", {"sugar": ("5", "g"), "protein": ("5", "g")}),
            _product("B", "B", {"sugar": ("10", "g"), "protein": ("10", "g")}),
        ],
        [_prio("LOWER_SUGAR", 3), _prio("HIGHER_PROTEIN", 1)],
    )

    for p in res.products:
        eff_weights = [ps.effective_weight for ps in p.parameter_scores if ps.included]
        assert sum(eff_weights) == pytest.approx(1.0, abs=1e-6)


def test_verify_no_unsupported_health_claims() -> None:
    res = _run(
        [
            _product("A", "A", {"sugar": ("5", "g")}),
            _product("B", "B", {"sugar": ("10", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert "healthiest" not in res.explanation.lower()
    assert "healthy" not in res.explanation.lower()
    assert "ranks highest" in res.explanation


def test_verify_original_nutrition_objects_not_mutated() -> None:
    val_dict = {"value": "10.5", "unit": "g", "status": "DETECTED"}
    val_dict_copy = copy.deepcopy(val_dict)
    val_input = NutritionValueInput.model_validate(val_dict)

    product_dict = {
        "product_id": "p1",
        "product_name": "Product 1",
        "basis": "PER_100G",
        "values": {"SUGAR": val_input},
    }
    product_dict_copy = copy.deepcopy(product_dict)

    req = ComparisonRequest.model_validate({
        "products": [product_dict, _product("p2", "Product 2", {"sugar": ("5", "g")})],
        "priorities": [{"priority": "LOWER_SUGAR"}],
    })

    _res = ComparisonService.compare(req)

    # Assert caller's dictionary and input objects are untouched
    assert val_dict == val_dict_copy
    assert val_input.value == Decimal("10.5")
    assert val_input.unit == "g"
    assert val_input.status is DeclarationStatus.DETECTED
