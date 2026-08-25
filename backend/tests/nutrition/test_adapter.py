"""Adapters that bridge already-extracted nutrition into comparison inputs.

These are the only functions that know the external payload shape, so they get
their own focused tests. No OCR/extraction is exercised or rebuilt here.
"""

from __future__ import annotations

import pytest

from app.nutrition.comparison import (
    ComparisonPriority,
    ComparisonRequest,
    Parameter,
    compare,
    product_from_nutrition_result,
    product_from_payload,
)
from app.schemas.nutrition import NutritionResult


def test_product_from_flat_payload_keeps_only_supported_keys():
    product = product_from_payload(
        "A",
        {"sugar": 5, "protein": 10, "serving_size": "30 g", "brand": "Acme"},
        display_name="Product A",
    )
    assert product.product_id == "A"
    assert product.display_name == "Product A"
    # serving_size / brand are not comparison parameters and are dropped.
    assert set(product.nutrients.keys()) == {"sugar", "protein"}


def test_product_from_payload_reads_value_unit_objects():
    product = product_from_payload(
        "A",
        {"sodium": {"value": 1, "unit": "g", "confidence": 0.9}},
    )
    # Extra keys like confidence must not break extra='forbid' downstream.
    reading = product.nutrients["sodium"]
    assert reading.value == 1
    assert reading.unit == "g"


def test_product_from_payload_handles_string_readings():
    product = product_from_payload("A", {"sugar": "1500 mg"})
    assert product.nutrients["sugar"] == "1500 mg"


def test_product_from_nutrition_result_available():
    result = NutritionResult(available=True, payload={"sugar": 4, "protein": 12})
    product = product_from_nutrition_result("A", result, display_name="Product A")
    assert product is not None
    assert product.product_id == "A"
    assert set(product.nutrients.keys()) == {"sugar", "protein"}


def test_product_from_nutrition_result_unavailable_returns_none():
    result = NutritionResult(available=False, payload=None)
    assert product_from_nutrition_result("A", result) is None


def test_product_from_nutrition_result_available_but_empty_payload_returns_none():
    result = NutritionResult(available=True, payload=None)
    assert product_from_nutrition_result("A", result) is None


def test_adapter_output_flows_through_compare():
    # Two extracted results -> adapt -> compare, end to end.
    r_a = NutritionResult(available=True, payload={"sugar": {"value": 1500, "unit": "mg"}})
    r_b = NutritionResult(available=True, payload={"sugar": {"value": 4, "unit": "g"}})
    products = [
        product_from_nutrition_result("A", r_a, display_name="Product A"),
        product_from_nutrition_result("B", r_b, display_name="Product B"),
    ]
    assert all(p is not None for p in products)

    result = compare(
        ComparisonRequest(
            products=products,
            priorities=[ComparisonPriority(parameter=Parameter.SUGAR)],
        )
    )
    # 1500 mg == 1.5 g < 4 g, so A wins after normalisation.
    assert result.winner == "A"


def test_adapter_accepts_duck_typed_result():
    # Anything exposing .available/.payload works, not just the Pydantic model.
    class Fake:
        available = True
        payload = {"sugar": 3}

    product = product_from_nutrition_result("A", Fake())
    assert product is not None
    assert product.nutrients["sugar"] == 3
