"""Phase 15: per-field declaration extraction behaviour (via the public service)."""

from app.core.enums import DetectionStatus
from app.extraction import extract_declarations
from app.schemas.extraction import ExtractionResult, FieldExtraction
from app.schemas.ocr import OCRResult


def _ocr(text: str, confidence: float = 0.95, bbox=(0, 0, 120, 20)) -> OCRResult:
    return OCRResult(text=text, confidence=confidence, bbox=list(bbox))


def _field(result: ExtractionResult, name: str) -> FieldExtraction | None:
    return next((f for f in result.fields if f.field == name), None)


def _values(field: FieldExtraction) -> set[str | None]:
    return {c.value for c in field.candidates}


# --------------------------------------------------------------------------- #
# MRP
# --------------------------------------------------------------------------- #


def test_mrp_clean_is_detected_with_numeric_value():
    result = extract_declarations([_ocr("MRP ₹50")])
    mrp = _field(result, "mrp")
    assert mrp is not None
    assert mrp.status is DetectionStatus.DETECTED
    assert mrp.best.value == "50"
    assert mrp.best.unit == "INR"


def test_mrp_letter_o_confusion_is_uncertain_not_silent_fifty():
    # The spec's canonical case: "MRP ₹5O" must NOT silently become MRP = 50.
    result = extract_declarations([_ocr("MRP ₹5O")])
    mrp = _field(result, "mrp")
    assert mrp is not None
    assert mrp.status is DetectionStatus.UNCERTAIN
    # Both the as-read and the corrected candidate are preserved.
    assert "5O" in _values(mrp)
    assert "50" in _values(mrp)


def test_mrp_strips_rupees_and_suffix():
    result = extract_declarations([_ocr("MRP Rs. 50/-")])
    mrp = _field(result, "mrp")
    assert mrp is not None and mrp.status is DetectionStatus.DETECTED
    assert mrp.best.value == "50"


def test_mrp_conflicting_values_are_uncertain_with_all_candidates():
    result = extract_declarations(
        [
            _ocr("MRP ₹50", bbox=(0, 0, 100, 20)),
            _ocr("M.R.P ₹60", bbox=(0, 40, 100, 60)),
        ]
    )
    mrp = _field(result, "mrp")
    assert mrp is not None
    assert mrp.status is DetectionStatus.UNCERTAIN  # do not arbitrarily pick
    assert {"50", "60"} <= _values(mrp)


def test_currency_word_inside_other_words_does_not_trigger_mrp():
    # "years"/"hours" contain "rs" but must not be read as a price.
    result = extract_declarations([_ocr("Best before 12 years from packing")])
    assert _field(result, "mrp") is None


# --------------------------------------------------------------------------- #
# Net quantity
# --------------------------------------------------------------------------- #


def test_net_quantity_detected_with_unit_string():
    result = extract_declarations([_ocr("Net Quantity: 500 g")])
    netq = _field(result, "net_quantity")
    assert netq is not None and netq.status is DetectionStatus.DETECTED
    assert netq.best.value == "500 g"  # engine-parseable (number + canonical unit)
    assert netq.best.unit == "g"


def test_net_quantity_value_in_adjacent_region_via_proximity():
    result = extract_declarations(
        [
            _ocr("Net Quantity", bbox=(0, 0, 100, 20)),
            _ocr("500 g", bbox=(110, 0, 180, 20)),  # same line, to the right
        ]
    )
    netq = _field(result, "net_quantity")
    assert netq is not None and netq.status is DetectionStatus.DETECTED
    assert netq.best.value == "500 g"


def test_net_quantity_confusion_is_uncertain():
    result = extract_declarations([_ocr("Net Wt 5OO g")])
    netq = _field(result, "net_quantity")
    assert netq is not None and netq.status is DetectionStatus.UNCERTAIN


def test_bare_quantity_without_keyword_is_not_net_quantity():
    # A stray "500 g" (could be a nutrition row) is not claimed as net quantity.
    result = extract_declarations([_ocr("Protein 5 g")])
    assert _field(result, "net_quantity") is None


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #


def test_manufacture_date_month_year():
    result = extract_declarations([_ocr("MFG: 05/2024")])
    mfg = _field(result, "manufacture_date")
    assert mfg is not None and mfg.status is DetectionStatus.DETECTED
    assert mfg.best.value == "05/2024"


def test_manufacture_date_month_name_is_normalised_to_numeric():
    result = extract_declarations([_ocr("Mfd: MAY 2024")])
    mfg = _field(result, "manufacture_date")
    assert mfg is not None and mfg.status is DetectionStatus.DETECTED
    assert mfg.best.value == "05/2024"


def test_manufacture_date_two_digit_year_is_uncertain():
    result = extract_declarations([_ocr("MFG 05/24")])
    mfg = _field(result, "manufacture_date")
    assert mfg is not None and mfg.status is DetectionStatus.UNCERTAIN


def test_packing_date_full_dmy():
    result = extract_declarations([_ocr("Packed on 12/05/2024")])
    pkd = _field(result, "packing_date")
    assert pkd is not None and pkd.status is DetectionStatus.DETECTED
    assert pkd.best.value == "12/05/2024"


# --------------------------------------------------------------------------- #
# Free-text declarations
# --------------------------------------------------------------------------- #


def test_manufacturer_detected():
    result = extract_declarations([_ocr("Manufactured by: ACME Foods Pvt Ltd, Pune")])
    mfr = _field(result, "manufacturer")
    assert mfr is not None and mfr.status is DetectionStatus.DETECTED
    assert "ACME Foods" in mfr.best.value


def test_consumer_care_email():
    result = extract_declarations([_ocr("Consumer Care: care@acme.com")])
    care = _field(result, "consumer_care")
    assert care is not None and care.status is DetectionStatus.DETECTED
    assert care.best.value == "care@acme.com"


def test_consumer_care_phone():
    result = extract_declarations([_ocr("Customer Care 1800 123 4567")])
    care = _field(result, "consumer_care")
    assert care is not None and care.status is DetectionStatus.DETECTED
    assert "1800" in care.best.value


def test_country_of_origin_detected():
    result = extract_declarations([_ocr("Country of Origin: India")])
    origin = _field(result, "country_of_origin")
    assert origin is not None and origin.status is DetectionStatus.DETECTED
    assert origin.best.value == "India"


def test_commodity_name_only_from_explicit_label():
    labelled = extract_declarations([_ocr("Name: Toor Dal")])
    assert _field(labelled, "commodity_name") is not None
    # A bare product name without a "Name:" label is not guessed at.
    unlabelled = extract_declarations([_ocr("Toor Dal")])
    assert _field(unlabelled, "commodity_name") is None


# --------------------------------------------------------------------------- #
# Layer separation & confidence
# --------------------------------------------------------------------------- #


def test_extraction_confidence_is_separate_from_ocr_confidence():
    result = extract_declarations([_ocr("MRP ₹50", confidence=0.9)])
    mrp = _field(result, "mrp")
    assert mrp.best.ocr_confidence == 0.9
    # Extraction confidence is derived, not equal to raw OCR confidence.
    assert mrp.best.extraction_confidence != 0.9
    assert 0.0 <= mrp.best.extraction_confidence <= 1.0


def test_low_ocr_confidence_pushes_field_to_uncertain():
    result = extract_declarations([_ocr("MRP ₹50", confidence=0.4)])
    mrp = _field(result, "mrp")
    # 0.4 * pattern weight < 0.6 => UNCERTAIN, even though the pattern is clean.
    assert mrp is not None and mrp.status is DetectionStatus.UNCERTAIN


def test_candidate_carries_source_reference_and_bbox():
    result = extract_declarations([_ocr("MRP ₹50", bbox=(10, 20, 110, 45))])
    mrp = _field(result, "mrp")
    assert mrp.best.source_reference == "ocr_region_0"
    assert mrp.best.bbox == [10, 20, 110, 45]


def test_empty_regions_yield_no_fields_with_warning():
    result = extract_declarations([_ocr("   ")])
    assert result.fields == []
    assert result.warnings


def test_devanagari_digits_extracted_as_ascii_value():
    result = extract_declarations([_ocr("MRP ₹ ५०")])
    mrp = _field(result, "mrp")
    assert mrp is not None and mrp.best.value == "50"
