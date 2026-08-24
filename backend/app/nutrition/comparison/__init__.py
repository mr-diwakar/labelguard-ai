"""
Multi-product nutrition comparison (LabelGuard AI, Phase 13).

Deterministic, explainable ranking of *already-extracted* product nutrition by
the consumer's selected priorities. No OCR, no extraction, no LLM, no medical
verdict — only relative statements about the parameters the consumer chose.

Public entry point:

    from app.nutrition.comparison import compare, ComparisonRequest

    result = compare(ComparisonRequest(products=[...], priorities=[...]))

To feed data from Teammate 2's ``NutritionResult``:

    from app.nutrition.comparison import product_from_nutrition_result
"""

from __future__ import annotations

from app.nutrition.comparison.parameters import (
    Direction,
    Parameter,
    supported_parameters,
)
from app.nutrition.comparison.schema import (
    ComparisonPriority,
    ComparisonRequest,
    ComparisonResult,
    CriterionSummary,
    NutrientValueInput,
    ParameterCell,
    ProductNutritionInput,
    ProductRanking,
)
from app.nutrition.comparison.service import (
    compare,
    product_from_nutrition_result,
    product_from_payload,
)

__all__ = [
    # Enums / vocabulary
    "Parameter",
    "Direction",
    "supported_parameters",
    # Request / response contracts
    "NutrientValueInput",
    "ProductNutritionInput",
    "ComparisonPriority",
    "ComparisonRequest",
    "ParameterCell",
    "CriterionSummary",
    "ProductRanking",
    "ComparisonResult",
    # Service + adapters
    "compare",
    "product_from_payload",
    "product_from_nutrition_result",
]
