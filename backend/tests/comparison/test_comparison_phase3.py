"""Phase 3: Multi-product nutrition comparison service & result generation tests.

Verifies:
- ComparisonService orchestrating full pipeline (ComparisonService.compare)
- Two products comparison
- Three products comparison
- Equal values handling
- Lower-is-better parameter direction
- Higher-is-better parameter direction
- User-selected priorities
- Ranking structure and scoring
- Ranking explanation generation (never claiming 'healthiest', using standard template)
- Trade-offs detection and explanation generation
- Missing data handling in service
- Single product comparison (rank 1, outcome SINGLE_PRODUCT, no comparative winner fabricated)
- Invalid input validation & empty product list rejection
- Deterministic result across repeated calls
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.comparison.service import ComparisonService
from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationStatus,
    NutritionParameter,
)
from app.schemas.comparison import ComparisonRequest, ComparisonResult


def _p(product_id: str, name: str, values: dict) -> dict:
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


def _compare(products: list[dict], priorities: list[dict]) -> ComparisonResult:
    req = ComparisonRequest.model_validate({"products": products, "priorities": priorities})
    return ComparisonService.compare(req)


# --- 1. Two products comparison ----------------------------------------------


def test_service_two_products_comparison() -> None:
    res = _compare(
        [
            _p("A", "Brand Alpha", {"sugar": ("10", "g")}),
            _p("B", "Brand Beta", {"sugar": ("4", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert len(res.products) == 2
    assert res.winner == "Brand Beta"
    assert res.ranking[0].product_id == "B"
    assert res.ranking[0].rank == 1
    assert res.ranking[1].product_id == "A"
    assert res.ranking[1].rank == 2
    assert "Brand Beta ranks highest" in res.explanation
    assert "healthiest" not in res.explanation.lower()


# --- 2. Three products comparison --------------------------------------------


def test_service_three_products_comparison() -> None:
    res = _compare(
        [
            _p("A", "Brand Alpha", {"sugar": ("15", "g"), "protein": ("4", "g")}),
            _p("B", "Brand Beta", {"sugar": ("8", "g"), "protein": ("10", "g")}),
            _p("C", "Brand Gamma", {"sugar": ("12", "g"), "protein": ("6", "g")}),
        ],
        [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 2)],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert len(res.products) == 3
    assert len(res.ranking) == 3
    assert res.ranking[0].product_id == "B"
    assert res.winner == "Brand Beta"


# --- 3. Equal values handling -------------------------------------------------


def test_service_equal_values_handling() -> None:
    res = _compare(
        [
            _p("A", "Brand Alpha", {"sugar": ("8", "g")}),
            _p("B", "Brand Beta", {"sugar": ("8", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.COMPLETED
    assert res.winner is None  # Tied, no single winner
    assert res.products[0].outcome is ComparisonOutcome.TIED
    assert res.products[1].outcome is ComparisonOutcome.TIED
    assert res.products[0].score == 0.5
    assert res.products[1].score == 0.5
    assert "tied" in res.explanation.lower()


# --- 4. Lower-is-better & Higher-is-better directions -------------------------


def test_service_lower_is_better_and_higher_is_better() -> None:
    res_lower = _compare(
        [_p("A", "A", {"sodium": ("400", "mg")}), _p("B", "B", {"sodium": ("100", "mg")})],
        [_prio("LOWER_SODIUM")],
    )
    assert res_lower.winner == "B"

    res_higher = _compare(
        [_p("A", "A", {"fiber": ("1", "g")}), _p("B", "B", {"fiber": ("5", "g")})],
        [_prio("HIGHER_FIBER")],
    )
    assert res_higher.winner == "B"


# --- 5. User-selected priorities ----------------------------------------------


def test_service_user_selected_priorities() -> None:
    res = _compare(
        [
            _p("A", "A", {"calories": ("300", "kcal"), "sugar": ("5", "g")}),
            _p("B", "B", {"calories": ("150", "kcal"), "sugar": ("15", "g")}),
        ],
        [_prio("LOWER_CALORIES", 5), _prio("LOWER_SUGAR", 1)],
    )

    # LOWER_CALORIES has weight 5; B has lower calories (150 vs 300). B wins.
    assert res.winner == "B"
    assert res.priorities_used[0].priority == ComparisonPriority.LOWER_CALORIES
    assert res.priorities_used[0].weight == 5


# --- 6. Ranking & explanation -------------------------------------------------


def test_service_ranking_and_explanation() -> None:
    res = _compare(
        [
            _p("A", "A", {"sugar": ("20", "g")}),
            _p("B", "B", {"sugar": ("5", "g")}),
        ],
        [_prio("LOWER_SUGAR")],
    )

    assert res.ranking[0].rank == 1
    assert res.ranking[0].product_id == "B"
    assert res.ranking[1].rank == 2
    assert res.ranking[1].product_id == "A"
    assert "B ranks highest based on your selected parameters" in res.explanation
    assert res.disclaimer is not None


# --- 7. Trade-offs generation -------------------------------------------------


def test_service_trade_offs_explanation() -> None:
    # Product B has lower sugar (5g vs 15g) and higher protein (10g vs 2g), so B wins overall.
    # But Product A has lower calories (100 kcal vs 250 kcal).
    # This generates a trade-off: Product B ranks higher based on lower sugar and higher protein, although Product A has lower calories.
    res = _compare(
        [
            _p("A", "Product A", {"sugar": ("15", "g"), "protein": ("2", "g"), "calories": ("100", "kcal")}),
            _p("B", "Product B", {"sugar": ("5", "g"), "protein": ("10", "g"), "calories": ("250", "kcal")}),
        ],
        [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 2), _prio("LOWER_CALORIES", 1)],
    )

    assert res.winner == "Product B"
    assert len(res.trade_offs) > 0
    trade_off_text = res.trade_offs[0]
    assert "Product B ranks higher" in trade_off_text
    assert "Product A has lower calories" in trade_off_text
    assert res.explanation == trade_off_text


# --- 8. Missing data handling -------------------------------------------------


def test_service_missing_data() -> None:
    # Product C is missing protein
    res = _compare(
        [
            _p("A", "A", {"sugar": ("5", "g"), "protein": ("10", "g")}),
            _p("B", "B", {"sugar": ("15", "g"), "protein": ("2", "g")}),
            _p("C", "C", {"sugar": ("10", "g"), "protein": None}),
        ],
        [_prio("LOWER_SUGAR"), _prio("HIGHER_PROTEIN")],
    )

    prod_c = next(p for p in res.products if p.product_id == "C")
    assert NutritionParameter.PROTEIN in prod_c.missing_parameters
    assert NutritionParameter.SUGAR in prod_c.available_parameters
    assert prod_c.score is not None
    assert prod_c.outcome is ComparisonOutcome.RANKED


# --- 9. Single product comparison ---------------------------------------------


def test_service_single_product_comparison() -> None:
    res = _compare(
        [_p("A", "Single Brand", {"sugar": ("10", "g")})],
        [_prio("LOWER_SUGAR")],
    )

    assert res.status is ComparisonStatus.SINGLE_PRODUCT
    assert res.winner is None  # Single product must not fabricate a comparative winner
    assert len(res.products) == 1
    assert res.products[0].rank == 1
    assert res.products[0].outcome is ComparisonOutcome.SINGLE_PRODUCT
    assert "Single Brand evaluated" in res.explanation
    assert "no competing products" in res.explanation.lower()


# --- 10. Invalid input & empty product list -----------------------------------


def test_service_invalid_input_empty_product_list() -> None:
    with pytest.raises(ValidationError):
        _compare([], [_prio("LOWER_SUGAR")])


def test_service_invalid_input_bad_weights() -> None:
    with pytest.raises(ValidationError):
        _compare(
            [_p("A", "A", {"sugar": ("5", "g")}), _p("B", "B", {"sugar": ("10", "g")})],
            [_prio("LOWER_SUGAR", 10)],
        )


# --- 11. Deterministic result --------------------------------------------------


def test_service_deterministic_result() -> None:
    products = [
        _p("A", "Product A", {"sugar": ("12", "g"), "protein": ("4", "g")}),
        _p("B", "Product B", {"sugar": ("6", "g"), "protein": ("8", "g")}),
    ]
    priorities = [_prio("LOWER_SUGAR", 2), _prio("HIGHER_PROTEIN", 1)]

    res1 = ComparisonService.compare(ComparisonRequest.model_validate({"products": products, "priorities": priorities}))
    res2 = ComparisonService.compare(ComparisonRequest.model_validate({"products": products, "priorities": priorities}))

    assert res1.model_dump() == res2.model_dump()
