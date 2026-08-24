"""Phase 5: published contracts parse the documented examples and reject illegal values."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.enums import DeclarationStatus
from app.schemas.compliance import ComplianceResult
from app.schemas.declaration import Declaration, DeclarationCheck
from app.schemas.inspection import InspectionResponse, InspectionSummary
from app.schemas.ocr import OCRResult
from app.schemas.scan import ScanResponse


def test_ocr_result_matches_teammate_contract() -> None:
    result = OCRResult.model_validate({"text": "MRP ₹50", "confidence": 0.98, "bbox": [100, 200, 300, 250]})

    assert result.text == "MRP ₹50"
    assert result.bbox == [100, 200, 300, 250]


def test_ocr_result_rejects_inverted_bbox() -> None:
    with pytest.raises(ValidationError):
        OCRResult.model_validate({"text": "MRP", "confidence": 0.9, "bbox": [300, 200, 100, 250]})


def test_declaration_contract_and_rejects_missing_status() -> None:
    declaration = Declaration.model_validate(
        {
            "field": "mrp",
            "value": "50",
            "confidence": 0.98,
            "source": "OCR",
            "bbox": [100, 200, 300, 250],
            "status": "DETECTED",
        }
    )

    assert declaration.status is DeclarationStatus.DETECTED

    with pytest.raises(ValidationError):
        Declaration.model_validate({"field": "mrp", "status": "MISSING"})


def test_compliance_result_matches_engine_contract() -> None:
    result = ComplianceResult.model_validate(
        {
            "status": "POTENTIAL_NON_COMPLIANCE",
            "rules_evaluated": 8,
            "passed": 6,
            "potential_violations": 1,
            "manual_review": 1,
            "violations": [
                {
                    "rule_id": "LM-PC-001",
                    "rule_code": "MRP_DECLARATION",
                    "description": "Potential issue detected",
                    "severity": "HIGH",
                    "confidence": 0.91,
                    "evidence_reference": None,
                    "recommended_action": "Manual verification recommended.",
                }
            ],
            "manual_review_items": [],
        }
    )

    assert result.potential_violations == 1
    assert result.violations[0].rule_code == "MRP_DECLARATION"


def test_confidence_cannot_exceed_one() -> None:
    with pytest.raises(ValidationError):
        OCRResult.model_validate({"text": "MRP", "confidence": 1.5, "bbox": [0, 0, 1, 1]})


def test_inspection_response_serialises_to_mobile_camel_case() -> None:
    payload = InspectionResponse(
        id=uuid4(),
        product_name="Tata Salt",
        inspected_at=datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc),
        category="Staples",
        assessment={
            "status": "COMPLIANT",
            "confidence": 0.96,
            "ruleReference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)",
            "passed": [{"declarationKey": "declaration.mrp", "confidence": 0.98}],
            "violations": [],
            "manualReview": [],
        },
    )

    dumped = payload.model_dump(by_alias=True)

    assert dumped["productName"] == "Tata Salt"
    assert dumped["inspectedAt"]
    assert dumped["assessment"]["ruleReference"].startswith("Legal Metrology")
    assert dumped["assessment"]["passed"][0]["declarationKey"] == "declaration.mrp"
    assert dumped["assessment"]["manualReview"] == []
    assert "product_name" not in dumped


def test_inspection_summary_matches_home_statistics() -> None:
    summary = InspectionSummary(total=12, compliant=8, manualReview=3, potentialIssues=1)

    assert summary.model_dump(by_alias=True) == {
        "total": 12,
        "compliant": 8,
        "manualReview": 3,
        "potentialIssues": 1,
    }


def test_scan_response_allows_null_nutrition() -> None:
    inspection = InspectionResponse(
        id=uuid4(),
        productName="Sample Product",
        inspectedAt=datetime(2026, 8, 23, tzinfo=timezone.utc),
        assessment={"status": "MANUAL_REVIEW", "passed": [], "violations": [], "manualReview": []},
    )
    compliance = ComplianceResult(
        status="MANUAL_REVIEW",
        rules_evaluated=1,
        passed=0,
        potential_violations=0,
        manual_review=1,
    )
    response = ScanResponse(
        inspection=inspection,
        compliance=compliance,
        nutrition=None,
        ingredients=[],
        report_status="FAILED",
        warnings=["Evidence generation unavailable. Manual verification recommended."],
    )

    assert response.nutrition is None
    assert response.ingredients == []
    assert response.report_status == "FAILED"


def test_declaration_check_bbox_must_be_normalised() -> None:
    with pytest.raises(ValidationError):
        DeclarationCheck.model_validate({"declarationKey": "declaration.mrp", "boundingBox": {"x": 2, "y": 0, "width": 0.1, "height": 0.1}})
