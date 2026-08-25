"""Phase 15: extraction service, DOWN-adapter, and alignment with engine parsers.

These tests assert the two seams that keep Phase 15 honest without importing the
compliance package into the extraction layer:
  * every value a DETECTED numeric field emits is re-parseable by the engine's own
    deterministic parsers (so extraction never emits something the engine rejects);
  * the extraction DETECTED threshold matches the engine's uncertain band.
"""

from app.compliance.validators.parsing import parse_mrp, parse_quantity
from app.compliance.validators.support import UNCERTAIN_CONFIDENCE_MAX
from app.core.enums import DetectionStatus
from app.extraction import extract_declarations
from app.extraction.extractors import DETECTED_CONFIDENCE_THRESHOLD
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.ocr import OCRResult


def _ocr(text: str, confidence: float = 0.95, bbox=(0, 0, 120, 20)) -> OCRResult:
    return OCRResult(text=text, confidence=confidence, bbox=list(bbox))


def test_extraction_threshold_matches_engine_uncertain_band():
    # If the engine's band moves, this test fails loudly rather than drifting.
    assert DETECTED_CONFIDENCE_THRESHOLD == UNCERTAIN_CONFIDENCE_MAX


def test_to_extracted_declarations_yields_valid_contract_objects():
    result = extract_declarations(
        [_ocr("MRP ₹50"), _ocr("Net Quantity 500 g"), _ocr("Country of Origin: India")]
    )
    declarations = result.to_extracted_declarations()
    assert declarations, "expected at least one extracted declaration"
    for declaration in declarations:
        assert isinstance(declaration, ExtractedDeclaration)
        # Extraction only ever asserts DETECTED or UNCERTAIN; it never claims a
        # reliable absence (CONFIRMED_ABSENT / NOT_DETECTED) from a single scan.
        assert declaration.status in {DetectionStatus.DETECTED, DetectionStatus.UNCERTAIN}


def test_detected_mrp_value_is_parseable_by_engine():
    result = extract_declarations([_ocr("MRP ₹50")])
    mrp = next(d for d in result.to_extracted_declarations() if d.field == "mrp")
    assert mrp.status is DetectionStatus.DETECTED
    assert parse_mrp(mrp.value) is not None  # engine will accept it


def test_detected_net_quantity_value_is_parseable_by_engine():
    result = extract_declarations([_ocr("Net Quantity 500 g")])
    netq = next(d for d in result.to_extracted_declarations() if d.field == "net_quantity")
    assert netq.status is DetectionStatus.DETECTED
    parsed = parse_quantity(netq.value)
    assert parsed is not None and str(parsed.unit) == "g"


def test_every_emitted_canonical_unit_is_engine_parseable():
    # The canonical units extraction emits are a subset the engine can parse.
    for unit in ("g", "kg", "ml", "l", "pcs"):
        assert parse_quantity(f"1 {unit}") is not None


def test_extractor_does_not_fabricate_absence():
    # No declarations at all -> empty output, never a CONFIRMED_ABSENT for every field.
    result = extract_declarations([_ocr("some unrelated text")])
    assert all(
        f.status in {DetectionStatus.DETECTED, DetectionStatus.UNCERTAIN} for f in result.fields
    )


def test_service_is_deterministic():
    regions = [_ocr("MRP ₹50"), _ocr("Net Quantity 500 g")]
    first = extract_declarations(regions).model_dump()
    second = extract_declarations(regions).model_dump()
    assert first == second
