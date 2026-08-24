"""End-to-end comparison through the public ``compare()`` entry point.

Each of the 14 required scenarios from the task brief is covered here and
labelled in the test name (S1..S14).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.nutrition.comparison import (
    ComparisonPriority,
    ComparisonRequest,
    Parameter,
    ProductNutritionInput,
    compare,
)
from app.nutrition.comparison.parameters import Direction


def _request(products, priorities):
    return ComparisonRequest(products=products, priorities=priorities)


def _product(pid, nutrients, name=None):
    return ProductNutritionInput(product_id=pid, display_name=name, nutrients=nutrients)


def _by_id(result):
    return {r.product_id: r for r in result.rankings}


# --------------------------------------------------------------------------- #
# S1 — two products
# --------------------------------------------------------------------------- #
def test_s1_two_products():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 10}, name="Product A"),
                _product("B", {"sugar": 4}, name="Product B"),
            ],
            [ComparisonPriority(parameter=Parameter.SUGAR)],
        )
    )
    assert result.winner == "B"
    assert result.winner_display_name == "Product B"
    assert len(result.rankings) == 2
    assert _by_id(result)["B"].rank == 1
    assert _by_id(result)["A"].rank == 2


# --------------------------------------------------------------------------- #
# S2 — three products
# --------------------------------------------------------------------------- #
def test_s2_three_products():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 10}),
                _product("B", {"sugar": 2}),
                _product("C", {"sugar": 6}),
            ],
            [ComparisonPriority(parameter=Parameter.SUGAR)],
        )
    )
    assert [r.product_id for r in result.rankings] == ["B", "C", "A"]
    assert result.winner == "B"


# --------------------------------------------------------------------------- #
# S3 — equal nutrition values across products
# --------------------------------------------------------------------------- #
def test_s3_equal_values_produce_tie_and_no_verdict():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 5, "protein": 8}),
                _product("B", {"sugar": 5, "protein": 8}),
            ],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN),
            ],
        )
    )
    assert result.tie is True
    assert all(r.score is None for r in result.rankings)
    # No parameter differentiates, so every criterion says so.
    assert all(c.differentiating is False for c in result.criteria)
    assert "tied" in result.explanation[0].lower()


# --------------------------------------------------------------------------- #
# S4 — different units are normalised before comparison
# --------------------------------------------------------------------------- #
def test_s4_different_units_normalised():
    # 1500 mg == 1.5 g < 4 g, so A has less sugar despite the larger number.
    result = compare(
        _request(
            [
                _product("A", {"sugar": "1500 mg"}),
                _product("B", {"sugar": "4 g"}),
            ],
            [ComparisonPriority(parameter=Parameter.SUGAR)],
        )
    )
    assert result.winner == "A"
    a_cell = next(c for c in _by_id(result)["A"].cells if c.parameter is Parameter.SUGAR)
    assert a_cell.unit == "g"
    assert a_cell.value == pytest.approx(1.5)


# --------------------------------------------------------------------------- #
# S5 — one product missing sugar
# --------------------------------------------------------------------------- #
def test_s5_missing_sugar_not_treated_as_zero():
    result = compare(
        _request(
            [
                _product("A", {"sugar": None, "protein": 10}),  # sugar not detected
                _product("B", {"sugar": 5, "protein": 20}),
            ],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN),
            ],
        )
    )
    a = _by_id(result)["A"]
    sugar_cell = next(c for c in a.cells if c.parameter is Parameter.SUGAR)
    assert sugar_cell.available is False
    assert sugar_cell.display == "NOT_DETECTED"
    assert sugar_cell.value is None  # never 0
    # Sugar has only one participant -> non-differentiating; ranking is on protein.
    assert Parameter.SUGAR in a.not_detected_parameters
    assert result.winner == "B"  # more protein


# --------------------------------------------------------------------------- #
# S6 — one product missing protein
# --------------------------------------------------------------------------- #
def test_s6_missing_protein():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 2, "protein": 15}),
                _product("B", {"sugar": 8, "protein": None}),  # protein not detected
            ],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN),
            ],
        )
    )
    b = _by_id(result)["B"]
    protein_cell = next(c for c in b.cells if c.parameter is Parameter.PROTEIN)
    assert protein_cell.available is False
    assert Parameter.PROTEIN in b.not_detected_parameters
    # A has lower sugar AND the only protein reading; A wins on sugar (the only
    # differentiating parameter).
    assert result.winner == "A"


# --------------------------------------------------------------------------- #
# S7 — a product missing multiple fields
# --------------------------------------------------------------------------- #
def test_s7_missing_multiple_fields_reduces_coverage():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 3, "protein": 12, "fiber": 5}),
                _product("B", {"sugar": 6, "protein": None, "fiber": None}),
            ],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN),
                ComparisonPriority(parameter=Parameter.FIBER),
            ],
        )
    )
    b = _by_id(result)["B"]
    assert Parameter.PROTEIN in b.not_detected_parameters
    assert Parameter.FIBER in b.not_detected_parameters
    # Only sugar differentiates (protein/fiber have a single participant each).
    # Both products are scored on sugar alone -> full coverage of the *scoreable* set.
    assert b.coverage == pytest.approx(1.0)
    assert result.winner == "A"  # lower sugar


# --------------------------------------------------------------------------- #
# S8 — lower-is-better parameters
# --------------------------------------------------------------------------- #
def test_s8_lower_is_better_family():
    result = compare(
        _request(
            [
                _product("A", {"sodium": 800, "saturated_fat": 5, "calories": 250}),
                _product("B", {"sodium": 300, "saturated_fat": 2, "calories": 180}),
            ],
            [
                ComparisonPriority(parameter=Parameter.SODIUM),
                ComparisonPriority(parameter=Parameter.SATURATED_FAT),
                ComparisonPriority(parameter=Parameter.CALORIES),
            ],
        )
    )
    # B is lower on all three lower-is-better parameters.
    assert result.winner == "B"
    assert _by_id(result)["B"].score == pytest.approx(100.0)
    assert _by_id(result)["A"].score == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# S9 — higher-is-better parameters
# --------------------------------------------------------------------------- #
def test_s9_higher_is_better_family():
    result = compare(
        _request(
            [
                _product("A", {"protein": 20, "fiber": 9}),
                _product("B", {"protein": 8, "fiber": 3}),
            ],
            [
                ComparisonPriority(parameter=Parameter.PROTEIN),
                ComparisonPriority(parameter=Parameter.FIBER),
            ],
        )
    )
    # A is higher on both higher-is-better parameters.
    assert result.winner == "A"
    assert _by_id(result)["A"].score == pytest.approx(100.0)


# --------------------------------------------------------------------------- #
# S10 — user-selected priorities steer the ranking
# --------------------------------------------------------------------------- #
def test_s10_user_priorities_and_weights():
    products = [
        _product("A", {"sugar": 0, "protein": 0}),
        _product("B", {"sugar": 10, "protein": 10}),
    ]
    # Prioritising low sugar -> A wins.
    low_sugar = compare(
        _request(products, [ComparisonPriority(parameter=Parameter.SUGAR)])
    )
    assert low_sugar.winner == "A"

    # Prioritising high protein -> B wins.
    high_protein = compare(
        _request(products, [ComparisonPriority(parameter=Parameter.PROTEIN)])
    )
    assert high_protein.winner == "B"

    # Weighting protein 4x over sugar -> B wins the blended score.
    weighted = compare(
        _request(
            products,
            [
                ComparisonPriority(parameter=Parameter.SUGAR, weight=1),
                ComparisonPriority(parameter=Parameter.PROTEIN, weight=4),
            ],
        )
    )
    assert weighted.winner == "B"
    # Only the selected parameters appear as criteria.
    assert {c.parameter for c in weighted.criteria} == {Parameter.SUGAR, Parameter.PROTEIN}


# --------------------------------------------------------------------------- #
# S11 — ranking explanation is comparative, never a health verdict
# --------------------------------------------------------------------------- #
def test_s11_explanation_language_and_highlights():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 10, "calories": 250}, name="Product A"),
                _product("B", {"sugar": 3, "calories": 300}, name="Product B"),
            ],
            [
                # Sugar weighted above calories so B's big sugar lead wins overall
                # even though A has fewer calories (a perfect 1:1 swap would tie).
                ComparisonPriority(parameter=Parameter.SUGAR, weight=2),
                ComparisonPriority(parameter=Parameter.CALORIES, weight=1),
            ],
        )
    )
    headline = result.explanation[0]
    # Required phrasing, and explicitly NOT a medical/"healthiest" claim.
    assert headline == "Product B ranks highest based on your selected parameters."
    assert "health" not in " ".join(result.explanation).lower()

    b_highlights = _by_id(result)["B"].highlights
    a_highlights = _by_id(result)["A"].highlights
    assert "✓ Lowest sugar" in b_highlights
    assert any(h.startswith("⚠") and "calories" in h for h in b_highlights)
    assert any("Higher sugar than Product B" in h for h in a_highlights)


# --------------------------------------------------------------------------- #
# S12 — invalid input
# --------------------------------------------------------------------------- #
def test_s12_invalid_input_duplicate_ids_raises():
    request = _request(
        [_product("dup", {"sugar": 1}), _product("dup", {"sugar": 2})],
        [ComparisonPriority(parameter=Parameter.SUGAR)],
    )
    with pytest.raises(ValueError, match="Duplicate product_id"):
        compare(request)


def test_s12_invalid_input_empty_product_id_rejected():
    with pytest.raises(ValidationError):
        ProductNutritionInput(product_id="   ", nutrients={"sugar": 1})


def test_s12_invalid_input_unsupported_parameter_rejected():
    with pytest.raises(ValidationError):
        ComparisonPriority(parameter="VITAMIN_C")


def test_s12_invalid_input_non_positive_weight_rejected():
    with pytest.raises(ValidationError):
        ComparisonPriority(parameter=Parameter.SUGAR, weight=0)


# --------------------------------------------------------------------------- #
# S13 — empty product list
# --------------------------------------------------------------------------- #
def test_s13_empty_product_list():
    result = compare(_request([], [ComparisonPriority(parameter=Parameter.SUGAR)]))
    assert result.rankings == []
    assert result.winner is None
    assert result.warnings
    assert "No products" in result.explanation[0]


# --------------------------------------------------------------------------- #
# S14 — single-product comparison
# --------------------------------------------------------------------------- #
def test_s14_single_product():
    result = compare(
        _request(
            [_product("A", {"sugar": 5, "protein": 10}, name="Solo")],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN),
            ],
        )
    )
    assert len(result.rankings) == 1
    assert result.rankings[0].product_id == "A"
    # Nothing to compare against -> no score, no winner, and a clear warning.
    assert result.rankings[0].score is None
    assert result.winner is None
    assert any("one product" in w.lower() for w in result.warnings)
    # The single product's cells still report its (available) values.
    assert all(c.available for c in result.rankings[0].cells)


# --------------------------------------------------------------------------- #
# Extra: unknown nutrients and no-priorities behaviour
# --------------------------------------------------------------------------- #
def test_unknown_nutrient_is_warned_not_scored():
    result = compare(
        _request(
            [
                _product("A", {"sugar": 2, "vitamin_c": 30}),
                _product("B", {"sugar": 6, "vitamin_c": 10}),
            ],
            [ComparisonPriority(parameter=Parameter.SUGAR)],
        )
    )
    assert any("vitamin_c" in w for w in result.warnings)
    assert result.winner == "A"


def test_no_priorities_lists_without_ranking():
    result = compare(_request([_product("A", {"sugar": 1}), _product("B", {"sugar": 2})], []))
    assert result.winner is None
    assert all(r.score is None for r in result.rankings)
    assert any("no comparison" in w.lower() for w in result.warnings)


def test_none_request_raises():
    with pytest.raises(ValueError):
        compare(None)
