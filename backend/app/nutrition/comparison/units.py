"""
Deterministic unit normalisation for nutrition values.

Every value is converted into the canonical unit of its parameter (see
``parameters.py``) so that products are compared on the same scale. Uses
``Decimal`` for exact conversion; the caller converts to float for scoring.

Conventions (documented, not guessed at scoring time):
* Mass family base unit is the gram. Energy family base unit is the kilocalorie.
* On nutrition labels "Calories" means kilocalories, so a bare ``cal``/``calorie``
  token is treated as ``kcal``. Kilojoules are converted with 1 kcal = 4.184 kJ.
* A missing/blank unit means "already in the canonical unit" — the common case
  when an extractor emits a bare number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from app.nutrition.comparison.parameters import Parameter, UnitFamily, spec_for

# Factor to convert one unit of the key into the family's base unit.
_MASS_TO_GRAM: dict[str, Decimal] = {
    "mcg": Decimal("0.000001"),
    "ug": Decimal("0.000001"),
    "µg": Decimal("0.000001"),
    "microgram": Decimal("0.000001"),
    "micrograms": Decimal("0.000001"),
    "mg": Decimal("0.001"),
    "milligram": Decimal("0.001"),
    "milligrams": Decimal("0.001"),
    "g": Decimal("1"),
    "gm": Decimal("1"),
    "gms": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
}

# 1 kcal = 4.184 kJ.
_KJ_PER_KCAL = Decimal("4.184")
_ENERGY_TO_KCAL: dict[str, Decimal] = {
    "kcal": Decimal("1"),
    "kilocalorie": Decimal("1"),
    "kilocalories": Decimal("1"),
    "cal": Decimal("1"),
    "calorie": Decimal("1"),
    "calories": Decimal("1"),
    "kj": Decimal("1") / _KJ_PER_KCAL,
    "kjoule": Decimal("1") / _KJ_PER_KCAL,
    "kilojoule": Decimal("1") / _KJ_PER_KCAL,
    "kilojoules": Decimal("1") / _KJ_PER_KCAL,
}

_FAMILY_TABLE: dict[UnitFamily, dict[str, Decimal]] = {
    UnitFamily.MASS: _MASS_TO_GRAM,
    UnitFamily.ENERGY: _ENERGY_TO_KCAL,
}

_NUMBER_UNIT = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([a-zA-Zµ]*)\s*$")


class NormalizationStatus(StrEnum):
    OK = "OK"
    NOT_DETECTED = "NOT_DETECTED"
    UNRECOGNIZED_UNIT = "UNRECOGNIZED_UNIT"
    INVALID_VALUE = "INVALID_VALUE"


@dataclass(frozen=True)
class NormalizedValue:
    status: NormalizationStatus
    value: float | None = None  # in the parameter's canonical unit
    canonical_unit: str | None = None
    raw_value: float | None = None
    raw_unit: str | None = None


def _clean_unit(unit: str) -> str:
    return unit.strip().lower().replace(".", "")


def split_value_unit(raw: str) -> tuple[Decimal, str | None] | None:
    """Parse a string like '5 g', '120kcal', '1,200 mg', '12' into (number, unit).

    Returns None when the string is not a leading-number measurement.
    """

    text = raw.strip().replace(",", "")
    match = _NUMBER_UNIT.match(text)
    if match is None:
        return None
    try:
        number = Decimal(match.group(1))
    except InvalidOperation:
        return None
    unit = match.group(2) or None
    return number, unit


def normalize(parameter: Parameter, value: object, unit: str | None = None) -> NormalizedValue:
    """Convert a raw (value, unit) into the parameter's canonical unit.

    ``value`` may be a number, a numeric string, or a string that carries its
    own unit (e.g. "5 g"). ``None``/blank value → NOT_DETECTED (never 0).
    A genuine, explicitly declared 0 is a real value and is kept.
    """

    spec = spec_for(parameter)
    table = _FAMILY_TABLE[spec.family]

    if value is None:
        return NormalizedValue(NormalizationStatus.NOT_DETECTED)

    number: Decimal | None
    parsed_unit = unit

    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        return NormalizedValue(NormalizationStatus.INVALID_VALUE)
    if isinstance(value, int | float):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return NormalizedValue(NormalizationStatus.INVALID_VALUE)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return NormalizedValue(NormalizationStatus.NOT_DETECTED)
        split = split_value_unit(stripped)
        if split is None:
            return NormalizedValue(NormalizationStatus.INVALID_VALUE)
        number, embedded_unit = split
        # An explicit unit argument wins over one embedded in the string.
        parsed_unit = unit or embedded_unit
    else:
        return NormalizedValue(NormalizationStatus.INVALID_VALUE)

    if number < 0:
        return NormalizedValue(NormalizationStatus.INVALID_VALUE)

    unit_token = _clean_unit(parsed_unit) if parsed_unit else _clean_unit(spec.canonical_unit)
    factor = table.get(unit_token)
    if factor is None:
        return NormalizedValue(
            NormalizationStatus.UNRECOGNIZED_UNIT,
            raw_value=float(number),
            raw_unit=parsed_unit,
        )

    base_value = number * factor
    canonical_factor = table[_clean_unit(spec.canonical_unit)]
    canonical_value = base_value / canonical_factor

    return NormalizedValue(
        status=NormalizationStatus.OK,
        value=float(canonical_value),
        canonical_unit=spec.canonical_unit,
        raw_value=float(number),
        raw_unit=parsed_unit,
    )
