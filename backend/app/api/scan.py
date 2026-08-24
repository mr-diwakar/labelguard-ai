from uuid import uuid4

from fastapi import APIRouter

from app.pipeline.orchestrator import run_scan
from app.schemas.contracts.scan import ScanRequest, ScanResult

router = APIRouter()


@router.post("/scan", response_model=ScanResult)
def scan(request: ScanRequest) -> ScanResult:
    """
    Run the unified LabelGuard scan pipeline.

    The legal engine is constructed server-side by the application.
    The API accepts already-structured OCR/verification inputs.
    """
    scan_id = request.scan_id or str(uuid4())

    return run_scan(
        scan_id=scan_id,
        ocr_results=request.ocr_results,
        context=request.context,
        verification_inputs=request.verification_inputs,
    )