"""
Public contracts for multi-product nutrition comparison.

These follow the existing ``APIModel`` convention (``extra='forbid'``,
``from_attributes=True``). The comparison service accepts already-extracted
nutrition data; it never performs OCR or nutrition extraction itself.

Input shape (conceptual):

    {
        "products": [ProductNutritionInput, ProductNutritionInput, ...],
        "priorities": [ComparisonPriority, ...]
    }

Output shape (conceptual):

    {
        "rankings": [...],
        "winner": "...",
        "criteria": [...],
        "explanation": [...],
        "warnings": [...]
    }
"""

from __future__ import annotations

from pydantic import Field, field_validator

from app.nutrition.comparison.parameters import Direction, Parameter
from app.schemas.common import APIModel


class NutrientValueInput(APIModel):
    """One nutrient reading for one product, as produced by extraction.

    ``value`` is None when the nutrient was not detected. It must never be
    coerced to 0. ``unit`` is optional; when omitted the value is assumed to be
    in the parameter's canonical unit.
    """

    value: float | None = None
    unit: str | None = None


class ProductNutritionInput(APIModel):
    """Already-extracted nutrition for a single product.

    ``nutrients`` maps a parameter name or extractor alias (e.g. "sugar",
    "total_sugars", "energy_kcal") to a reading. A plain number or numeric
    string is also accepted and wrapped as a unit-less reading.
    """

    product_id: str
    display_name: str | None = None
    nutrients: dict[str, NutrientValueInput | float | str | None] = Field(default_factory=dict)

    @field_validator("product_id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("product_id must be a non-empty string")
        return value


class ComparisonPriority(APIModel):
    """A parameter the consumer chose to compare on, with an optional weight
    and direction override. Weight defaults to 1.0; the service rescales weights
    so their absolute magnitude does not matter, only their ratios."""

    parameter: Parameter
    weight: float = Field(default=1.0, gt=0)
    direction: Direction | None = None


class ComparisonRequest(APIModel):
    products: list[ProductNutritionInput] = Field(default_factory=list)
    priorities: list[ComparisonPriority] = Field(default_factory=list)


class ParameterCell(APIModel):
    """Normalised per-product, per-parameter cell shown in the comparison table."""

    parameter: Parameter
    available: bool
    value: float | None = None  # canonical unit; None when NOT_DETECTED
    unit: str | None = None
    display: str  # "5 g" or "NOT_DETECTED"
    sub_score: float | None = None  # 0..1 within this parameter; None if not scored
    note: str | None = None  # e.g. why a cell was excluded from scoring


class CriterionSummary(APIModel):
    """How one selected priority behaved across the product set."""

    parameter: Parameter
    direction: Direction
    weight: float  # rescaled weight in 0..1
    display_name: str
    differentiating: bool  # False when <2 products have it, or all values equal
    participating_products: int
    note: str | None = None
    best_product_id: str | None = None
    not_detected_product_ids: list[str] = Field(default_factory=list)


class ProductRanking(APIModel):
    rank: int
    product_id: str
    display_name: str
    score: float | None  # 0..100; None when the product has no scored parameters
    coverage: float  # fraction of scored priorities this product had data for (0..1)
    scored_parameters: list[Parameter] = Field(default_factory=list)
    not_detected_parameters: list[Parameter] = Field(default_factory=list)
    cells: list[ParameterCell] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)  # "✓ ...", "⚠ ..."


class ComparisonResult(APIModel):
    """Deterministic, explainable comparison output.

    ``winner`` is the highest-ranked product id, or None when nothing could be
    scored. Language is comparative ("ranks highest based on your selected
    parameters"), never a health verdict.
    """

    rankings: list[ProductRanking] = Field(default_factory=list)
    winner: str | None = None
    winner_display_name: str | None = None
    criteria: list[CriterionSummary] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tie: bool = False
