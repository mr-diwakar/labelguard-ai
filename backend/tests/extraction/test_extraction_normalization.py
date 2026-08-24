"""Phase 15: deterministic text normalisation for declaration extraction."""

from app.extraction.normalization import (
    canonical_quantity_unit,
    contains_digit_confusion,
    correct_digit_confusion,
    is_pure_number,
    month_number,
    normalize_text,
)


def test_normalize_collapses_whitespace_and_trims():
    assert normalize_text("  MRP   ₹50 \n") == "MRP ₹50"


def test_normalize_maps_devanagari_digits_to_ascii():
    # A bilingual label may print the value in Devanagari digits; value is script-free.
    assert normalize_text("MRP ₹ ५०") == "MRP ₹ 50"


def test_normalize_empty_is_empty():
    assert normalize_text("") == ""


def test_is_pure_number():
    assert is_pure_number("50")
    assert is_pure_number("50.5")
    assert is_pure_number("-3")
    assert not is_pure_number("5O")
    assert not is_pure_number("50 g")


def test_contains_digit_confusion_flags_mixed_tokens():
    assert contains_digit_confusion("5O")  # digit + letter-oh
    assert contains_digit_confusion("l0")  # ell + digit
    assert not contains_digit_confusion("50")  # clean
    assert not contains_digit_confusion("abc")  # no digit => not a misread number


def test_correct_digit_confusion_is_a_candidate_not_a_rewrite():
    assert correct_digit_confusion("5O") == "50"
    assert correct_digit_confusion("l0") == "10"
    assert correct_digit_confusion("50") == "50"


def test_canonical_quantity_unit_maps_aliases():
    assert canonical_quantity_unit("gm") == "g"
    assert canonical_quantity_unit("grams") == "g"
    assert canonical_quantity_unit("KG") == "kg"
    assert canonical_quantity_unit("ml") == "ml"
    assert canonical_quantity_unit("litre") == "l"
    assert canonical_quantity_unit("nos") == "pcs"
    assert canonical_quantity_unit("oz") is None  # unrecognised


def test_month_number():
    assert month_number("may") == 5
    assert month_number("Jan") == 1
    assert month_number("DECEMBER") == 12
    assert month_number("sept") == 9
    assert month_number("xyz") is None
