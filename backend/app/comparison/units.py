"""Deterministic unit normalisation for the multi-product nutrition comparison (Phase 13).

The repository stores extracted nutrition as a free-form payload and pins no unit vocabulary
of its own. The only existing unit map, :mod:`app.compliance.validators.parsing`, covers legal
*net-quantity* units (g/kg/ml/l/pcs) and deliberately excludes the energy and sub-gram mass
units a nutrition panel uses. This module therefore *mirrors* that module's pattern -- an alias
table plus :class:`~decimal.Decimal` arithmetic -- with a nutrition-specific vocabulary, rather
than importing the legal parser, so the two domains stay decoupled.

Guarantees:
    * Deterministic: all arithmetic uses :class:`~decimal.Decimal`; the single non-terminating
      conversion (kJ to kcal) is quantised to a fixed resolution with ``ROUND_HALF_UP``.
    * Non-destructive: the original magnitude, unit and status are preserved on the result and
      the caller's input is never mutated; a fresh :class:`NormalizedValue` is returned.
    * Honest about gaps: a missing value stays ``NOT_DETECTED`` and is never coerced to zero;
      an unrecognised or dimensionally-wrong unit is flagged, never guessed.

``NormalizationStatus`` is intentionally local to this module: it is an internal processing
outcome consumed by the comparison service, not part of the published schema vocabulary in
``app.core.enums``. Scoring and ranking live in a later phase; this module only produces a
comparable magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from enum import StrEnum

from app.core.enums import DeclarationStatus, NutritionParameter
from app.schemas.comparison import NutritionValueInput

# Canonical magnitudes are rounded to this many decimal places so repeated conversions
# (notably kJ to kcal) are reproducible. Six places keeps microgram-scale values clear of
# zero while erasing division noise from the one non-terminating conversion.
CANONICAL_DECIMAL_PLACES = 6
_QUANTUM = Decimal("0.000001")
_CONVERSION_PRECISION = 28

# FSSAI / Codex Alimentarius energy equivalence: 1 kcal = 4.184 kJ.
_KJ_PER_KCAL = Decimal("4.184")


class _Dimension(StrEnum):
    """The physical quantity a unit measures. Units only convert within one dimension."""

    MASS = "MASS"
    ENERGY = "ENERGY"


class NormalizationStatus(StrEnum):
    """Outcome of normalising a single nutrition value."""

    NORMALIZED = "NORMALIZED"  # a comparable canonical magnitude was produced
    NOT_DETECTED = "NOT_DETECTED"  # nothing to normalise; never treated as zero
    UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"  # unit unknown, or wrong dimension for the parameter
    INVALID_VALUE = "INVALID_VALUE"  # magnitude present but not a usable non-negative finite number


# Canonical unit tokens mapped to the dimension they measure.
_UNIT_DIMENSION: dict[str, _Dimension] = {
    "g": _Dimension.MASS,
    "mg": _Dimension.MASS,
    "ug": _Dimension.MASS,
    "kcal": _Dimension.ENERGY,
    "kj": _Dimension.ENERGY,
}

# Factor to convert a unit into its dimension's base unit (gram for mass, kilojoule for
# energy) by multiplication. Only kcal-to-kJ and kJ-to-kcal are non-trivial.
_UNIT_TO_BASE: dict[str, Decimal] = {
    "g": Decimal(1),
    "mg": Decimal("0.001"),
    "ug": Decimal("0.000001"),
    "kj": Decimal(1),
    "kcal": _KJ_PER_KCAL,
}

# Accepted spellings mapped to a canonical unit token, mirroring the alias-table pattern in
# ``app.compliance.validators.parsing``. Bare "cal"/"calorie" is deliberately absent: on a
# panel it means kcal, but as a raw unit string it is a 1000x ambiguity we refuse to guess.
UNIT_ALIASES: dict[str, str] = {
    # mass
    "g": "g",
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    "mg": "mg",
    "milligram": "mg",
    "milligrams": "mg",
    "ug": "ug",
    "mcg": "ug",
    "µg": "ug",  # micro sign + g
    "microgram": "ug",
    "micrograms": "ug",
    # energy
    "kcal": "kcal",
    "kcals": "kcal",
    "kilocalorie": "kcal",
    "kilocalories": "kcal",
    "kj": "kj",
    "kjs": "kj",
    "kilojoule": "kj",
    "kilojoules": "kj",
}

# Per-parameter canonical unit. Sodium is compared in milligrams (as declared on Indian
# labels); every other mass parameter in grams; energy in kilocalories.
_SODIUM_CANONICAL = "mg"
_ENERGY_CANONICAL = "kcal"
_MASS_CANONICAL = "g"


def canonical_unit_for(parameter: NutritionParameter) -> str:
    """The unit every value of ``parameter`` is normalised to for comparison."""
    if parameter is NutritionParameter.CALORIES:
        return _ENERGY_CANONICAL
    if parameter is NutritionParameter.SODIUM:
        return _SODIUM_CANONICAL
    return _MASS_CANONICAL


@dataclass(frozen=True)
class NormalizedValue:
    """The immutable result of normalising one value; preserves the original input.

    ``canonical_value`` and ``canonical_unit`` are populated only when ``status`` is
    ``NORMALIZED`` -- that magnitude is what the comparison should compare on. For every other
    status they are ``None``, never zero.
    """

    parameter: NutritionParameter
    status: NormalizationStatus
    canonical_value: Decimal | None
    canonical_unit: str | None
    original_value: Decimal | None
    original_unit: str | None
    original_status: DeclarationStatus
    detail: str

    @property
    def is_comparable(self) -> bool:
        """True when a canonical magnitude is available to compare on."""
        return self.status is NormalizationStatus.NORMALIZED


def _to_canonical(value: Decimal, unit_token: str, canonical_token: str) -> Decimal:
    """Convert ``value`` (in ``unit_token``) to ``canonical_token`` deterministically."""
    with localcontext() as ctx:
        ctx.prec = _CONVERSION_PRECISION
        base = value * _UNIT_TO_BASE[unit_token]
        canonical = base / _UNIT_TO_BASE[canonical_token]
        return canonical.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


def normalize_value(
    parameter: NutritionParameter,
    value: Decimal | None,
    unit: str | None,
    status: DeclarationStatus = DeclarationStatus.DETECTED,
) -> NormalizedValue:
    """Normalise one nutrition magnitude to its parameter's canonical unit.

    Returns a :class:`NormalizedValue`; it never raises for bad data and never mutates the
    input. Missing values (``status`` NOT_DETECTED, or no magnitude) yield ``NOT_DETECTED``
    with no magnitude -- never zero. A negative or non-finite magnitude yields
    ``INVALID_VALUE``. An unknown or dimensionally incompatible unit yields
    ``UNSUPPORTED_UNIT``. A magnitude with no unit is assumed to already be canonical.
    """

    def _result(
        result_status: NormalizationStatus,
        canonical_value: Decimal | None,
        canonical_unit: str | None,
        detail: str,
    ) -> NormalizedValue:
        return NormalizedValue(
            parameter=parameter,
            status=result_status,
            canonical_value=canonical_value,
            canonical_unit=canonical_unit,
            original_value=value,
            original_unit=unit,
            original_status=status,
            detail=detail,
        )

    # 1. Missing -- never invented, never zero.
    if status is DeclarationStatus.NOT_DETECTED or value is None:
        return _result(
            NormalizationStatus.NOT_DETECTED,
            None,
            None,
            "No value was detected; this parameter is left out of the comparison for this product.",
        )

    # 2. Defensive validation. The input schema already blocks these, but the normalisation
    #    layer must not trust upstream: a magnitude must be finite and non-negative.
    if not value.is_finite() or value < 0:
        return _result(
            NormalizationStatus.INVALID_VALUE,
            None,
            None,
            f"Value {value} is not a usable non-negative number.",
        )

    canonical_unit = canonical_unit_for(parameter)
    dimension = _UNIT_DIMENSION[canonical_unit]

    # 3. A unit-less magnitude is assumed to already be in the canonical unit.
    resolved = canonical_unit if unit is None else UNIT_ALIASES.get(unit.strip().lower())
    if resolved is None:
        return _result(
            NormalizationStatus.UNSUPPORTED_UNIT,
            None,
            None,
            f"Unit {unit!r} is not a recognised nutrition unit.",
        )

    # 4. The unit must measure the same dimension as the parameter (e.g. no kJ for sugar).
    if _UNIT_DIMENSION[resolved] is not dimension:
        return _result(
            NormalizationStatus.UNSUPPORTED_UNIT,
            None,
            None,
            f"Unit {resolved!r} does not measure {parameter.value.lower()}.",
        )

    canonical_value = _to_canonical(value, resolved, canonical_unit)
    if unit is None:
        detail = f"No unit supplied; assumed {canonical_value} {canonical_unit}."
    elif resolved == canonical_unit:
        detail = f"Already in {canonical_unit}."
    else:
        detail = f"Converted {value} {resolved} to {canonical_value} {canonical_unit}."
    return _result(NormalizationStatus.NORMALIZED, canonical_value, canonical_unit, detail)


def normalize_input(parameter: NutritionParameter, item: NutritionValueInput) -> NormalizedValue:
    """Normalise a :class:`~app.schemas.comparison.NutritionValueInput`.

    Thin adapter over :func:`normalize_value` so the comparison service can normalise the
    already-extracted values it holds without unpacking them by hand.
    """
    return normalize_value(parameter, item.value, item.unit, item.status)
