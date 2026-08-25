"""
Phase 12: PaddleOCR adapter.

These tests never require paddleocr to be installed. They verify the adapter is
importable without it, that the import is lazy, and that the result parser is
robust — the actual engine is exercised only in manual/integration runs.
"""

import sys

from app.ocr.paddle_adapter import PaddleOCRProvider, _parse_paddle_result
from app.ocr.provider import RawTextRegion


def test_importing_adapter_does_not_import_paddleocr():
    # Merely importing the module must not pull in the heavy dependency.
    if not PaddleOCRProvider.available():
        assert "paddleocr" not in sys.modules


def test_available_returns_bool():
    assert isinstance(PaddleOCRProvider.available(), bool)


def test_provider_name_lists_languages():
    assert PaddleOCRProvider(["en"]).name == "paddleocr:en"
    assert PaddleOCRProvider(["en", "hi"]).name == "paddleocr:en+hi"


def test_provider_defaults_to_english_when_empty():
    assert PaddleOCRProvider([]).name == "paddleocr:en"


def test_parse_classic_paddle_result():
    raw = [
        [
            [[[10, 20], [110, 20], [110, 60], [10, 60]], ("MRP 50", 0.97)],
            [[[10, 70], [200, 70], [200, 110], [10, 110]], ("NET 100 g", 0.88)],
        ]
    ]
    regions = _parse_paddle_result(raw)
    assert len(regions) == 2
    assert all(isinstance(r, RawTextRegion) for r in regions)
    assert regions[0].text == "MRP 50"
    assert regions[0].confidence == 0.97
    assert regions[0].box[0] == (10.0, 20.0)


def test_parse_handles_empty_and_none():
    assert _parse_paddle_result(None) == []
    assert _parse_paddle_result([]) == []
    assert _parse_paddle_result([None]) == []


def test_parse_skips_malformed_entries():
    raw = [[["not", "a", "valid", "entry"], [[[0, 0], [1, 1]], ("ok", 0.5)]]]
    regions = _parse_paddle_result(raw)
    # The malformed entry is skipped; the valid one survives.
    assert len(regions) == 1
    assert regions[0].text == "ok"
