"""Multi-product nutrition comparison endpoint (Phase 13).

Thin HTTP layer over ``app.nutrition.comparison.compare``. It performs no OCR
or nutrition extraction — it ranks *already-extracted* product nutrition by the
consumer's selected priorities. The request/response bodies are validated by the
comparison module's own Pydantic schemas.
"""

from fastapi import APIRouter

from app.core.exceptions import AppError
from app.nutrition.comparison import ComparisonRequest, ComparisonResult, compare

router = APIRouter()


@router.post(
    "/nutrition/compare",
    response_model=ComparisonResult,
    summary="Compare already-scanned products by selected nutrition priorities",
)
def compare_nutrition(request: ComparisonRequest) -> ComparisonResult:
    """Rank already-extracted product nutrition by the consumer's priorities.

    Deterministic and explainable; no medical verdict. Structurally invalid
    requests (e.g. a duplicate ``product_id``) return HTTP 400; malformed JSON
    is rejected as 422 by the schema before reaching this handler.
    """

    try:
        return compare(request)
    except ValueError as exc:
        raise AppError("INVALID_COMPARISON", str(exc), status_code=400) from exc
