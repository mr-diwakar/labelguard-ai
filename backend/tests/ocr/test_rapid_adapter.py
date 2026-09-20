"""RapidOCR adapter tests. Never require the package to be installed."""

import sys

from app.ocr.provider import RawTextRegion
from app.ocr.rapid_adapter import RapidOCRProvider, _parse_rapid_result


def test_importing_adapter_does_not_import_rapidocr():
    if not RapidOCRProvider.available():
        assert "rapidocr" not in sys.modules
        assert "rapidocr_onnxruntime" not in sys.modules


def test_available_returns_bool():
    assert isinstance(RapidOCRProvider.available(), bool)


def test_provider_name_lists_languages():
    assert RapidOCRProvider(["en"]).name == "rapidocr:en"
    assert RapidOCRProvider(["en", "hi"]).name == "rapidocr:en+hi"


def test_parse_list_of_box_text_score():
    raw = [
        [[[10, 20], [110, 20], [110, 60], [10, 60]], "MRP 50", 0.97],
        [[[10, 70], [200, 70], [200, 110], [10, 110]], "NET 100 g", 0.88],
    ]
    regions = _parse_rapid_result(raw)
    assert len(regions) == 2
    assert all(isinstance(r, RawTextRegion) for r in regions)
    assert regions[0].text == "MRP 50"
    assert regions[0].confidence == 0.97
    assert regions[0].box[0] == (10.0, 20.0)


def test_parse_tuple_payload():
    raw = ([[[[0, 0], [1, 0], [1, 1], [0, 1]], "ok", 0.5]], 0.01)
    regions = _parse_rapid_result(raw)
    assert len(regions) == 1
    assert regions[0].text == "ok"


def test_parse_handles_empty_and_none():
    assert _parse_rapid_result(None) == []
    assert _parse_rapid_result([]) == []
    assert _parse_rapid_result((None, 0.0)) == []


def test_parse_skips_malformed_entries():
    raw = [["not", "valid"], [[[0, 0], [1, 1]], "ok", 0.5]]
    regions = _parse_rapid_result(raw)
    assert len(regions) == 1
    assert regions[0].text == "ok"


def test_parse_object_with_boxes_txts_scores():
    class _Output:
        boxes = [[[10, 20], [110, 20], [110, 60], [10, 60]]]
        txts = ["MRP 50"]
        scores = [0.97]

    regions = _parse_rapid_result(_Output())
    assert len(regions) == 1
    assert regions[0].text == "MRP 50"
    assert regions[0].confidence == 0.97
