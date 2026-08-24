"""Phase 12: OCRService orchestration over an injectable provider."""

import numpy as np
import pytest

pytest.importorskip("numpy")

from app.core.enums import OCRStatus
from app.ocr.provider import RawTextRegion
from app.ocr.service import OCRService
from tests.fixtures.images import StubOCRProvider

_IMAGE = np.zeros((100, 100, 3), np.uint8)
_BOX = [(10.0, 10.0), (40.0, 10.0), (40.0, 30.0), (10.0, 30.0)]


def test_service_returns_success_for_confident_regions():
    provider = StubOCRProvider([RawTextRegion(text="HELLO", confidence=0.9, box=_BOX)], name="stub")
    resp = OCRService(provider).run(_IMAGE, width=100, height=100)
    assert resp.status is OCRStatus.SUCCESS
    assert resp.provider == "stub"
    assert resp.regions[0].text == "HELLO"


def test_service_converts_provider_failure_to_processing_error():
    provider = StubOCRProvider(raises=RuntimeError("model weights missing at /secret/path"))
    resp = OCRService(provider).run(_IMAGE, width=100, height=100)
    assert resp.status is OCRStatus.PROCESSING_ERROR
    assert resp.regions == []
    # The raw exception text must not leak into the client-facing warning.
    joined = " ".join(resp.warnings)
    assert "secret" not in joined and "RuntimeError" not in joined


def test_service_maps_bboxes_back_to_original_space():
    provider = StubOCRProvider([RawTextRegion(text="X", confidence=0.9, box=[(100.0, 100.0), (200.0, 200.0)])])
    # Provider saw a half-scale image, so multiply coordinates back by 2.
    resp = OCRService(provider).run(_IMAGE, width=1000, height=1000, scale_x=0.5, scale_y=0.5)
    assert resp.regions[0].bbox == [200, 200, 400, 400]
