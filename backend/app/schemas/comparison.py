"""Contracts for the multi-product nutrition comparison (Phase 13).

These schemas only define the data shapes. Scoring, normalisation and ranking are
implemented by a later, deterministic and LLM-free engine; every result field here is
populated by that engine.

Design notes for reviewers:
    * Already-extracted values enter through :class:`NutritionValueInput`. This is a new
      post-extraction contract, distinct from the OCR ``Declaration`` and from the
      teammate ``NutritionResult`` envelope, so the comparison can reason over typed
      magnitudes and units without duplicating any existing nutrition model.
    * A missing value is ``NOT_DETECTED`` with no magnitude. It is never zero.
    * A comparison is informational only. It is never a health, dietary or legal verdict,
      and it never labels a product "healthiest".
"""

from decimal import Decimal
from typing import Self

from pydantic import Field, field_validator, model_validator

from app.core.enums import (
    ComparisonOutcome,
    ComparisonPriority,
    ComparisonStatus,
    DeclarationSource,
    DeclarationStatus,
    NutritionBasis,
    NutritionParameter,
    ParameterDirection,
)
from app.schemas.common import APIModel

MIN_COMPARISON_PRODUCTS = 1
MAX_COMPARISON_PRODUCTS = 5

DISCLAIMER = (
    "This comparison ranks the selected products only on the nutrition parameters you "
    "chose, using the values declared on their labels. It is informational and is not "
    "medical, dietary or legal advice."
)



# --- Input contracts ---------------------------------------------------------


class NutritionValueInput(APIModel):
    """One already-extracted nutrition value for one product.

    The magnitude and unit are kept separate so the comparison can normalise units
    deterministically. A missing value is expressed with ``status = NOT_DETECTED`` and
    no magnitude; it is never represented as zero.

    Example:
        {"value": "10.5", "unit": "g", "status": "DETECTED", "confidence": 0.97}
    """

    value: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=16)
    status: DeclarationStatus = DeclarationStatus.DETECTED
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: DeclarationSource = DeclarationSource.OCR

    @field_validator("value")
    @classmethod
    def _reject_non_finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("value must be a finite number")
        return value

    @field_validator("unit")
    @classmethod
    def _normalise_unit(cls, unit: str | None) -> str | None:
        if unit is None:
            return None
        return unit.strip() or None

    @model_validator(mode="after")
    def _magnitude_matches_status(self) -> Self:
        has_value = self.value is not None
        if (
            self.status in (DeclarationStatus.DETECTED, DeclarationStatus.MANUALLY_VERIFIED)
            and not has_value
        ):
            raise ValueError(f"a {self.status.value} value must include a magnitude")
        if self.status is DeclarationStatus.NOT_DETECTED and has_value:
            raise ValueError("a NOT_DETECTED value must not include a magnitude")
        return self


class ComparisonProductInput(APIModel):
    """A single product entering the comparison, keyed by already-extracted values.

    ``values`` carries only the parameters that were extracted for this product;
    parameters absent from the map are treated as NOT_DETECTED by the comparison, never
    as zero. Unknown parameter keys are rejected.

    Example:
        {
            "product_id": "prod-a",
            "product_name": "Brand A Biscuits",
            "basis": "PER_100G",
            "values": {"SUGAR": {"value": "22", "unit": "g"}}
        }
    """

    product_id: str = Field(min_length=1, max_length=128)
    product_name: str = Field(min_length=1, max_length=256)
    basis: NutritionBasis = NutritionBasis.PER_100G
    values: dict[NutritionParameter, NutritionValueInput] = Field(default_factory=dict)

    @field_validator("product_id", "product_name")
    @classmethod
    def _strip_identifier(cls, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class PriorityWeight(APIModel):
    """A selected comparison priority and its optional relative weight.

    Weight is optional and defaults to 1, which makes every selected priority equal.

    Example:
        {"priority": "LOWER_SUGAR", "weight": 3}
    """

    priority: ComparisonPriority
    weight: int = Field(default=1, ge=1, le=5)


class ComparisonRequest(APIModel):
    """The full comparison input: the products to compare and the chosen priorities.

    Example:
        {
            "products": [
                {"product_id": "a", "product_name": "Brand A", "values": {"SUGAR": {"value": "22", "unit": "g"}}},
                {"product_id": "b", "product_name": "Brand B", "values": {"SUGAR": {"value": "9", "unit": "g"}}}
            ],
            "priorities": [{"priority": "LOWER_SUGAR", "weight": 2}]
        }
    """

    products: list[ComparisonProductInput] = Field(
        min_length=MIN_COMPARISON_PRODUCTS, max_length=MAX_COMPARISON_PRODUCTS
    )
    priorities: list[PriorityWeight] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_products_and_priorities(self) -> Self:
        ids = [product.product_id for product in self.products]
        if len(set(ids)) != len(ids):
            raise ValueError("product_id values must be unique")
        chosen = [item.priority for item in self.priorities]
        if len(set(chosen)) != len(chosen):
            raise ValueError("each priority may be selected only once")
        return self


# --- Result contracts (populated by the scoring engine in a later phase) -----


class ParameterScore(APIModel):
    """How one product fared on one parameter.

    ``included`` is False when the parameter could not take part (e.g. missing for this
    product, or comparable across fewer than two products). The fields make the arithmetic
    fully explainable: ``weighted_contribution = normalized_score * effective_weight``, and
    a product's final score is the sum of ``weighted_contribution`` over its included
    parameters. ``weight`` is the raw priority weight (1-5); ``effective_weight`` is that
    weight re-normalised so a product's included effective weights sum to 1.
    """

    parameter: NutritionParameter
    direction: ParameterDirection
    canonical_value: Decimal | None = Field(default=None, ge=0)
    unit: str | None = None
    status: DeclarationStatus
    included: bool = False
    normalized_score: float | None = Field(default=None, ge=0, le=1)
    weight: int | None = Field(default=None, ge=1, le=5)
    effective_weight: float | None = Field(default=None, ge=0, le=1)
    weighted_contribution: float | None = Field(default=None, ge=0)
    note: str = ""


class ProductComparisonResult(APIModel):
    """A product's overall standing in the comparison. Not a health verdict.

    ``rank`` and ``score`` are absent when the product could not be ranked.
    ``available_parameters`` are the active parameters this product was scored on;
    ``missing_parameters`` are the active parameters it lacked (never scored as zero).
    ``coverage`` is ``len(available_parameters) / number of active parameters``.
    """

    product_id: str = Field(min_length=1, max_length=128)
    product_name: str = Field(min_length=1, max_length=256)
    rank: int | None = Field(default=None, ge=1)
    score: float | None = Field(default=None, ge=0, le=1)
    outcome: ComparisonOutcome
    coverage: float = Field(ge=0, le=1)
    parameter_scores: list[ParameterScore] = Field(default_factory=list)
    available_parameters: list[NutritionParameter] = Field(default_factory=list)
    missing_parameters: list[NutritionParameter] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""


class RankEntry(APIModel):
    """One row of the ordered ranking table (standard competition ranking)."""

    rank: int = Field(ge=1)
    product_id: str = Field(min_length=1, max_length=128)
    product_name: str = Field(min_length=1, max_length=256)
    score: float | None = Field(default=None, ge=0, le=1)


class ExcludedParameter(APIModel):
    """A parameter left out of scoring, with a human-readable reason."""

    parameter: NutritionParameter
    reason: str = Field(min_length=1)


class ComparisonResult(APIModel):
    """The complete, explainable comparison outcome.

    Produced by the scoring engine; this schema fixes the contract.
    The ranking reflects only the selected parameters and the values declared on labels.
    """

    status: ComparisonStatus
    winner: str | None = None
    ranking: list[RankEntry] = Field(default_factory=list)
    products: list[ProductComparisonResult] = Field(default_factory=list)
    active_parameters: list[NutritionParameter] = Field(default_factory=list)
    excluded_parameters: list[ExcludedParameter] = Field(default_factory=list)
    priorities_used: list[PriorityWeight] = Field(default_factory=list)
    explanation: str = ""
    trade_offs: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)

