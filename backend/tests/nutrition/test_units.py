"""Unit normalisation: canonical conversion, missing-vs-zero, bad input.

Covers required scenario (4) different units, and the NOT_DETECTED-never-zero
rule at the lowest level.
"""

from __future__ import annotations

import pytest

from app.nutrition.comparison.parameters import Parameter
from app.nutrition.comparison.units import (
    NormalizationStatus,
    normalize,
    split_value_unit,
)


def test_missing_value_is_not_detected_never_zero():
    result = normalize(Parameter.SUGAR, None)
    assert result.status is NormalizationStatus.NOT_DETECTED
    assert result.value is None  # crucially not 0.0


def test_blank_string_is_not_detected():
    result = normalize(Parameter.SUGAR, "   ")
    assert result.status is NormalizationStatus.NOT_DETECTED
    assert result.value is None


def test_explicit_zero_is_a_real_value():
    result = normalize(Parameter.SUGAR, 0)
    assert result.status is NormalizationStatus.OK
    assert result.value == 0.0


def test_bare_number_assumed_canonical_unit():
    result = normalize(Parameter.SUGAR, 5)
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(5.0)
    assert result.canonical_unit == "g"


def test_mass_conversion_mg_to_g():
    result = normalize(Parameter.SUGAR, 1500, "mg")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(1.5)


def test_sodium_canonical_is_mg_and_g_converts_up():
    # Sodium's canonical unit is mg, so 1 g -> 1000 mg.
    result = normalize(Parameter.SODIUM, 1, "g")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(1000.0)
    assert result.canonical_unit == "mg"


def test_energy_kj_to_kcal():
    # 4.184 kJ == 1 kcal.
    result = normalize(Parameter.CALORIES, 418.4, "kj")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(100.0)
    assert result.canonical_unit == "kcal"


def test_energy_bare_calories_token_is_kcal():
    # On labels "Calories" means kcal.
    result = normalize(Parameter.CALORIES, 200, "cal")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(200.0)


def test_embedded_unit_in_string():
    result = normalize(Parameter.SUGAR, "1500 mg")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(1.5)


def test_explicit_unit_argument_overrides_embedded():
    # Caller-supplied unit wins over the one in the string.
    result = normalize(Parameter.SUGAR, "1500 mg", "g")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(1500.0)


def test_comma_grouped_number():
    result = normalize(Parameter.CALORIES, "1,200 kcal")
    assert result.status is NormalizationStatus.OK
    assert result.value == pytest.approx(1200.0)


def test_unrecognized_unit_is_flagged_not_zero():
    result = normalize(Parameter.SUGAR, 5, "cups")
    assert result.status is NormalizationStatus.UNRECOGNIZED_UNIT
    assert result.value is None
    assert result.raw_unit == "cups"


def test_negative_is_invalid():
    result = normalize(Parameter.SUGAR, -3)
    assert result.status is NormalizationStatus.INVALID_VALUE
    assert result.value is None


def test_bool_rejected_as_invalid():
    # bool is an int subclass; it must not be read as 1/0.
    result = normalize(Parameter.SUGAR, True)
    assert result.status is NormalizationStatus.INVALID_VALUE


def test_non_numeric_string_invalid():
    result = normalize(Parameter.SUGAR, "lots")
    assert result.status is NormalizationStatus.INVALID_VALUE


def test_wrong_family_unit_is_unrecognized():
    # kcal is meaningless for a mass parameter.
    result = normalize(Parameter.SUGAR, 5, "kcal")
    assert result.status is NormalizationStatus.UNRECOGNIZED_UNIT


@pytest.mark.parametrize(
    "raw,expected_number,expected_unit",
    [
        ("5 g", 5, "g"),
        ("120kcal", 120, "kcal"),
        ("12", 12, None),
        ("1,200 mg", 1200, "mg"),
        ("0.5 g", 0.5, "g"),
    ],
)
def test_split_value_unit(raw, expected_number, expected_unit):
    parsed = split_value_unit(raw)
    assert parsed is not None
    number, unit = parsed
    assert float(number) == pytest.approx(expected_number)
    assert unit == expected_unit


def test_split_value_unit_rejects_non_measurement():
    assert split_value_unit("not a number") is None
