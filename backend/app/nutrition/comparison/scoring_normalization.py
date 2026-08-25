"""
Build a normalised value table from already-extracted product nutrition.

Turns each product's raw nutrient map into ``{product_id: {Parameter:
NormalizedValue}}`` in canonical units, resolving extractor aliases and
recording warnings for anything unusable. Missing/blank values become
NOT_DETECTED; they are never turned into 0.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.nutrition.comparison.parameters import Parameter, display_name, resolve_parameter
from app.nutrition.comparison.schema import NutrientValueInput, ProductNutritionInput
from app.nutrition.comparison.units import NormalizationStatus, NormalizedValue, normalize

# product_id -> parameter -> normalized value
NormalizedTable = dict[str, dict[Parameter, NormalizedValue]]


def _normalize_one(parameter: Parameter, raw: NutrientValueInput | float | str | None) -> NormalizedValue:
    if raw is None:
        return NormalizedValue(NormalizationStatus.NOT_DETECTED)
    if isinstance(raw, NutrientValueInput):
        return normalize(parameter, raw.value, raw.unit)
    return normalize(parameter, raw, None)


def build_normalized_table(products: Sequence[ProductNutritionInput]) -> tuple[NormalizedTable, list[str]]:
    table: NormalizedTable = {}
    warnings: list[str] = []

    for product in products:
        cells: dict[Parameter, NormalizedValue] = {}
        for raw_key, raw_value in product.nutrients.items():
            parameter = resolve_parameter(raw_key)
            if parameter is None:
                warnings.append(
                    f"Product '{product.product_id}': nutrient '{raw_key}' is not a supported "
                    f"comparison parameter and was ignored."
                )
                continue
            if parameter in cells and cells[parameter].status is NormalizationStatus.OK:
                warnings.append(
                    f"Product '{product.product_id}': duplicate value for {display_name(parameter)} "
                    f"('{raw_key}') was ignored; the first reading is used."
                )
                continue

            normalized = _normalize_one(parameter, raw_value)
            if normalized.status is NormalizationStatus.UNRECOGNIZED_UNIT:
                warnings.append(
                    f"Product '{product.product_id}': {display_name(parameter)} unit "
                    f"'{normalized.raw_unit}' was not recognised; the value was excluded."
                )
            elif normalized.status is NormalizationStatus.INVALID_VALUE:
                warnings.append(
                    f"Product '{product.product_id}': {display_name(parameter)} value could not be "
                    f"read as a non-negative number; the value was excluded."
                )
            cells[parameter] = normalized
        table[product.product_id] = cells

    return table, warnings
