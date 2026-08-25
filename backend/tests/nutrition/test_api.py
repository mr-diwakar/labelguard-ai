"""HTTP endpoint wiring for nutrition comparison.

Exercises the route handler directly rather than through Starlette's
``TestClient``: this environment's TestClient requires an ``httpx2`` package
that is not installed (a pre-existing, unrelated dependency gap). Calling the
handler still verifies the request/response models, the ``compare()`` call, and
the ValueError -> HTTP 400 mapping. It also avoids importing ``app.api.router``
(which pulls in settings) by importing only the feature's own sub-router.
"""

from __future__ import annotations

import pytest

from app.api.nutrition import compare_nutrition, router
from app.core.exceptions import AppError
from app.nutrition.comparison import (
    ComparisonPriority,
    ComparisonRequest,
    ComparisonResult,
    Parameter,
    ProductNutritionInput,
)


def _request(products, priorities):
    return ComparisonRequest(products=products, priorities=priorities)


def test_route_is_registered_as_post():
    registered = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
    assert (("POST",), "/nutrition/compare") in registered


def test_handler_returns_comparison_result():
    result = compare_nutrition(
        _request(
            [
                ProductNutritionInput(product_id="A", display_name="Product A",
                                      nutrients={"sugar": "10 g", "protein": 5}),
                ProductNutritionInput(product_id="B", display_name="Product B",
                                      nutrients={"sugar": "1500 mg", "protein": 9}),
            ],
            [
                ComparisonPriority(parameter=Parameter.SUGAR),
                ComparisonPriority(parameter=Parameter.PROTEIN, weight=2),
            ],
        )
    )
    assert isinstance(result, ComparisonResult)
    assert result.winner == "B"
    assert result.explanation[0] == "Product B ranks highest based on your selected parameters."


def test_duplicate_product_ids_map_to_http_400():
    request = _request(
        [
            ProductNutritionInput(product_id="X", nutrients={"sugar": 1}),
            ProductNutritionInput(product_id="X", nutrients={"sugar": 2}),
        ],
        [ComparisonPriority(parameter=Parameter.SUGAR)],
    )
    with pytest.raises(AppError) as excinfo:
        compare_nutrition(request)
    assert excinfo.value.status_code == 400
    assert excinfo.value.code == "INVALID_COMPARISON"
