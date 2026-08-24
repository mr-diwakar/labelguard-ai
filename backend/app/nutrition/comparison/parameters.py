"""
Registry of nutrition parameters the comparison feature understands.

This module owns *only* static, deterministic vocabulary: which parameters are
comparable, their canonical unit, the physical family used for unit
normalisation, a conventional "which direction is better" default, and the raw
label aliases an extractor might emit.

Nothing here reads product data, scores, or makes a health claim. The default
direction is a *comparison convenience* (e.g. when a consumer says "compare on
sugar" without saying "lower"), never medical or dietary advice. A caller can
override the direction on any priority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Parameter(StrEnum):
    """Supported comparison parameters. Values match the PROJECT_CONTEXT list."""

    CALORIES = "CALORIES"
    SUGAR = "SUGAR"
    ADDED_SUGAR = "ADDED_SUGAR"
    PROTEIN = "PROTEIN"
    CARBOHYDRATES = "CARBOHYDRATES"
    FAT = "FAT"
    SATURATED_FAT = "SATURATED_FAT"
    TRANS_FAT = "TRANS_FAT"
    FIBER = "FIBER"
    SODIUM = "SODIUM"


class Direction(StrEnum):
    """Which way is 'better' for ranking. This is a preference, not a verdict."""

    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"


class UnitFamily(StrEnum):
    """Physical family used to pick the unit-conversion table."""

    MASS = "MASS"
    ENERGY = "ENERGY"


@dataclass(frozen=True)
class ParameterSpec:
    parameter: Parameter
    display_name: str
    family: UnitFamily
    canonical_unit: str
    default_direction: Direction
    aliases: tuple[str, ...]


# The canonical unit is the unit every value of that parameter is converted to
# before scoring, so cross-product comparison is apples-to-apples.
_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec(Parameter.CALORIES, "calories", UnitFamily.ENERGY, "kcal", Direction.LOWER_IS_BETTER,
                  ("calories", "calorie", "energy", "energy_kcal", "kcal", "cal")),
    ParameterSpec(Parameter.SUGAR, "sugar", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("sugar", "sugars", "total_sugar", "total_sugars", "of_which_sugars")),
    ParameterSpec(Parameter.ADDED_SUGAR, "added sugar", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("added_sugar", "added_sugars", "added_sugars_g")),
    ParameterSpec(Parameter.PROTEIN, "protein", UnitFamily.MASS, "g", Direction.HIGHER_IS_BETTER,
                  ("protein", "proteins")),
    ParameterSpec(Parameter.CARBOHYDRATES, "carbohydrates", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("carbohydrates", "carbohydrate", "carbs", "total_carbohydrate", "total_carbohydrates")),
    ParameterSpec(Parameter.FAT, "fat", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("fat", "total_fat", "fats")),
    ParameterSpec(Parameter.SATURATED_FAT, "saturated fat", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("saturated_fat", "saturates", "saturated", "sat_fat", "of_which_saturates")),
    ParameterSpec(Parameter.TRANS_FAT, "trans fat", UnitFamily.MASS, "g", Direction.LOWER_IS_BETTER,
                  ("trans_fat", "trans", "trans_fatty_acids", "trans_fats")),
    ParameterSpec(Parameter.FIBER, "fiber", UnitFamily.MASS, "g", Direction.HIGHER_IS_BETTER,
                  ("fiber", "fibre", "dietary_fiber", "dietary_fibre")),
    ParameterSpec(Parameter.SODIUM, "sodium", UnitFamily.MASS, "mg", Direction.LOWER_IS_BETTER,
                  ("sodium", "na", "sodium_mg")),
)

SPEC_BY_PARAMETER: dict[Parameter, ParameterSpec] = {spec.parameter: spec for spec in _SPECS}


def _normalise_key(raw: str) -> str:
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


_ALIAS_INDEX: dict[str, Parameter] = {}
for _spec in _SPECS:
    _ALIAS_INDEX[_normalise_key(_spec.parameter.value)] = _spec.parameter
    for _alias in _spec.aliases:
        _ALIAS_INDEX[_normalise_key(_alias)] = _spec.parameter


def spec_for(parameter: Parameter) -> ParameterSpec:
    return SPEC_BY_PARAMETER[parameter]


def resolve_parameter(raw: str) -> Parameter | None:
    """Map a raw label/key (e.g. 'Total Sugars', 'energy_kcal') to a Parameter.

    Returns None for anything outside the supported set. Callers treat an
    unresolved key as data that is simply not comparable, never as zero.
    """

    if not raw:
        return None
    return _ALIAS_INDEX.get(_normalise_key(raw))


def default_direction(parameter: Parameter) -> Direction:
    return SPEC_BY_PARAMETER[parameter].default_direction


def canonical_unit(parameter: Parameter) -> str:
    return SPEC_BY_PARAMETER[parameter].canonical_unit


def display_name(parameter: Parameter) -> str:
    return SPEC_BY_PARAMETER[parameter].display_name


def supported_parameters() -> tuple[Parameter, ...]:
    return tuple(spec.parameter for spec in _SPECS)
