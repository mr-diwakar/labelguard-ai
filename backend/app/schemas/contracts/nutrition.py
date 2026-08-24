"""
Nutrition data contract (Phase 11).

Shape only — no nutrition/FSSAI engine is implemented here (that is a later phase).
The one invariant this layer enforces is the spec's hard rule: MISSING nutrition data
is never zero.

Two distinct "not a number" cases are representable, and neither is 0.0:
  * a nutrient field left as None  -> the nutrient was not extracted at all (unknown);
  * a NutritionValue with amount=None -> the line was seen but its number could not be
    read (UNCERTAIN).
A genuine declared "0 g" (e.g. "Trans Fat 0 g") is amount=0.0 with status DETECTED and
is the only way a zero can appear. status reuses DetectionStatus (no new vocabulary).

Complements the existing NutritionResult (the teammate availability wrapper); it does
not replace it.
"""

from pydantic import Field

from app.core.enums import DetectionStatus
from app.schemas.common import APIModel


class NutritionValue(APIModel):
    """
    One nutrient amount.

    amount is None by default = unknown. It is never silently 0. A real declared zero
    is amount=0.0 with status=DETECTED.
    """

    amount: float | None = None
    unit: str | None = None
    status: DetectionStatus | None = None
    source_reference: str | None = None

    @property
    def is_known(self) -> bool:
        """True only when a concrete amount was extracted."""
        return self.amount is not None


class NutritionFacts(APIModel):
    """
    A nutrition panel. Every nutrient defaults to None (unknown), so an empty
    NutritionFacts() carries no implied zeros.

    Example:
        {
            "basis": "PER_100G",
            "serving_size": "30 g",
            "energy": {"amount": 250, "unit": "kcal", "status": "DETECTED"},
            "trans_fat": {"amount": 0, "unit": "g", "status": "DETECTED"},
            "added_sugar": null
        }
    """

    basis: str | None = None
    serving_size: str | None = None

    energy: NutritionValue | None = None
    protein: NutritionValue | None = None
    carbohydrates: NutritionValue | None = None
    total_sugar: NutritionValue | None = None
    added_sugar: NutritionValue | None = None
    fat: NutritionValue | None = None
    saturated_fat: NutritionValue | None = None
    trans_fat: NutritionValue | None = None
    fiber: NutritionValue | None = None
    sodium: NutritionValue | None = None
