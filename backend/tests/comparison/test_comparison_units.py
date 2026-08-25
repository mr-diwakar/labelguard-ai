"""Phase 13: deterministic unit normalisation for the nutrition comparison.

Covers same-unit pass-through, valid conversions (energy and mass), missing values,
unsupported and dimensionally-wrong units, invalid magnitudes, and rounding behaviour.
Scoring and ranking are a later phase and are not exercised here.
"""

from decimal import Decimal

import pytest

from app.comparison.units import (
    CANONICAL_DECIMAL_PLACES,
    NormalizationStatus,
    canonical_unit_for,
    normalize_input,
    normalize_value,
)
from app.core.enums import DeclarationStatus, NutritionParameter
from app.schemas.comparison import NutritionValueInput

# --- 1. same units -----------------------------------------------------------


def test_same_unit_is_passed_through_unchanged() -> None:
    result = normalize_value(NutritionParameter.SUGAR, Decimal("10"), "g")

    assert result.status is NormalizationStatus.NORMALIZED
    assert result.canonical_unit == "g"
    assert result.canonical_value == Decimal("10")
    assert result.is_comparable


def test_same_unit_aliases_resolve_to_the_canonical_unit() -> None:
    spelled_out = normalize_value(NutritionParameter.PROTEIN, Decimal("8"), "grams")
    upper_case = normalize_value(NutritionParameter.PROTEIN, Decimal("8"), "G")

    assert spelled_out.canonical_value == upper_case.canonical_value == Decimal("8")
    assert spelled_out.canonical_unit == "g"


# --- 2. different valid units ------------------------------------------------


def test_sodium_grams_convert_to_canonical_milligrams() -> None:
    # Sodium is compared in mg; a label declaring 0.2 g becomes 200 mg.
    result = normalize_value(NutritionParameter.SODIUM, Decimal("0.2"), "g")

    assert result.canonical_unit == "mg"
    assert result.canonical_value == Decimal("200")


def test_sodium_milligrams_are_already_canonical() -> None:
    result = normalize_value(NutritionParameter.SODIUM, Decimal("200"), "mg")

    assert result.canonical_unit == "mg"
    assert result.canonical_value == Decimal("200")


# --- 3. energy conversion ----------------------------------------------------


def test_energy_kilojoules_convert_to_kilocalories() -> None:
    # 418.4 kJ = 100 kcal exactly (1 kcal = 4.184 kJ).
    result = normalize_value(NutritionParameter.CALORIES, Decimal("418.4"), "kJ")

    assert result.canonical_unit == "kcal"
    assert result.canonical_value == Decimal("100")


def test_energy_kilocalories_are_already_canonical() -> None:
    result = normalize_value(NutritionParameter.CALORIES, Decimal("250"), "kcal")

    assert result.canonical_unit == "kcal"
    assert result.canonical_value == Decimal("250")


# --- 4. mass conversion ------------------------------------------------------


def test_mass_milligrams_convert_to_grams() -> None:
    result = normalize_value(NutritionParameter.PROTEIN, Decimal("5000"), "mg")

    assert result.canonical_unit == "g"
    assert result.canonical_value == Decimal("5")


def test_mass_micrograms_convert_to_grams() -> None:
    result = normalize_value(NutritionParameter.FIBER, Decimal("2500000"), "mcg")

    assert result.canonical_unit == "g"
    assert result.canonical_value == Decimal("2.5")


# --- 5. missing values -------------------------------------------------------


def test_not_detected_status_yields_a_not_detected_result() -> None:
    result = normalize_value(
        NutritionParameter.SUGAR, None, None, DeclarationStatus.NOT_DETECTED
    )

    assert result.status is NormalizationStatus.NOT_DETECTED
    assert result.canonical_value is None
    assert not result.is_comparable


def test_missing_magnitude_is_never_coerced_to_zero() -> None:
    # A detected-but-empty magnitude (e.g. low-confidence with no number) stays not-detected.
    result = normalize_value(
        NutritionParameter.SUGAR, None, "g", DeclarationStatus.LOW_CONFIDENCE
    )

    assert result.status is NormalizationStatus.NOT_DETECTED
    assert result.canonical_value is None
    assert result.canonical_value != Decimal("0")


# --- 6. unsupported units ----------------------------------------------------


def test_unknown_unit_is_flagged_not_guessed() -> None:
    result = normalize_value(NutritionParameter.SUGAR, Decimal("5"), "cups")

    assert result.status is NormalizationStatus.UNSUPPORTED_UNIT
    assert result.canonical_value is None


def test_energy_unit_on_a_mass_parameter_is_unsupported() -> None:
    # kJ measures energy; sugar is a mass. The dimensions must match.
    result = normalize_value(NutritionParameter.SUGAR, Decimal("5"), "kJ")

    assert result.status is NormalizationStatus.UNSUPPORTED_UNIT


def test_mass_unit_on_an_energy_parameter_is_unsupported() -> None:
    result = normalize_value(NutritionParameter.CALORIES, Decimal("5"), "g")

    assert result.status is NormalizationStatus.UNSUPPORTED_UNIT


def test_ambiguous_calorie_unit_is_not_assumed_to_be_kcal() -> None:
    # "cal" is 1/1000 kcal; refusing to guess avoids a silent 1000x mis-scaling.
    result = normalize_value(NutritionParameter.CALORIES, Decimal("250"), "cal")

    assert result.status is NormalizationStatus.UNSUPPORTED_UNIT


# --- 7. invalid values -------------------------------------------------------


def test_negative_magnitude_is_invalid() -> None:
    result = normalize_value(NutritionParameter.SUGAR, Decimal("-1"), "g")

    assert result.status is NormalizationStatus.INVALID_VALUE
    assert result.canonical_value is None


def test_non_finite_magnitude_is_invalid() -> None:
    for bad in (Decimal("NaN"), Decimal("Infinity")):
        result = normalize_value(NutritionParameter.SUGAR, bad, "g")
        assert result.status is NormalizationStatus.INVALID_VALUE


# --- 8. precision / rounding behaviour ---------------------------------------


def test_energy_conversion_rounds_half_up_to_fixed_precision() -> None:
    # 100 kJ / 4.184 = 23.9005736... -> 6 dp, half-up -> 23.900574.
    result = normalize_value(NutritionParameter.CALORIES, Decimal("100"), "kJ")

    assert result.canonical_value == Decimal("23.900574")
    assert -result.canonical_value.as_tuple().exponent == CANONICAL_DECIMAL_PLACES


def test_normalisation_is_deterministic_and_repeatable() -> None:
    first = normalize_value(NutritionParameter.CALORIES, Decimal("2093"), "kJ")
    second = normalize_value(NutritionParameter.CALORIES, Decimal("2093"), "kJ")

    assert first.canonical_value == second.canonical_value


# --- preservation, adapters and metadata -------------------------------------


def test_original_input_is_preserved_on_the_result() -> None:
    result = normalize_value(
        NutritionParameter.SODIUM, Decimal("0.2"), " G ", DeclarationStatus.MANUALLY_VERIFIED
    )

    assert result.original_value == Decimal("0.2")
    assert result.original_unit == " G "  # raw, untouched
    assert result.original_status is DeclarationStatus.MANUALLY_VERIFIED
    assert result.canonical_value == Decimal("200")  # normalisation still applied


def test_unitless_value_is_assumed_to_be_canonical() -> None:
    result = normalize_value(NutritionParameter.SUGAR, Decimal("12"), None)

    assert result.status is NormalizationStatus.NORMALIZED
    assert result.canonical_unit == "g"
    assert result.canonical_value == Decimal("12")


def test_normalize_input_adapts_a_schema_value() -> None:
    item = NutritionValueInput.model_validate({"value": "5000", "unit": "mg"})
    result = normalize_input(NutritionParameter.PROTEIN, item)

    assert result.canonical_value == Decimal("5")
    assert result.original_value == Decimal("5000")


def test_normalize_input_passes_missing_through_as_not_detected() -> None:
    item = NutritionValueInput.model_validate({"status": "NOT_DETECTED"})
    result = normalize_input(NutritionParameter.SUGAR, item)

    assert result.status is NormalizationStatus.NOT_DETECTED
    assert result.canonical_value is None


@pytest.mark.parametrize(
    ("parameter", "expected"),
    [
        (NutritionParameter.CALORIES, "kcal"),
        (NutritionParameter.SODIUM, "mg"),
        (NutritionParameter.SUGAR, "g"),
        (NutritionParameter.PROTEIN, "g"),
        (NutritionParameter.TRANS_FAT, "g"),
    ],
)
def test_canonical_unit_for_each_parameter(parameter: NutritionParameter, expected: str) -> None:
    assert canonical_unit_for(parameter) == expected


def test_every_parameter_has_a_canonical_unit() -> None:
    # Guards against a new NutritionParameter arriving without a unit mapping.
    for parameter in NutritionParameter:
        assert canonical_unit_for(parameter) in {"g", "mg", "kcal"}
