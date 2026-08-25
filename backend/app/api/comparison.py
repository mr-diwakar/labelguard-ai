"""Multi-product nutrition comparison API endpoint (Phase 13 / Phase 3)."""

from fastapi import APIRouter

from app.comparison.service import ComparisonService
from app.schemas.comparison import ComparisonRequest, ComparisonResult

router = APIRouter()


@router.post(
    "/comparison",
    response_model=ComparisonResult,
    summary="Compare multi-product nutrition",
    description="Deterministically ranks and compares multiple products based on selected nutrition parameters and user priorities.",
)
def compare_products(request: ComparisonRequest) -> ComparisonResult:
    """Compare 1 to 5 products on selected nutrition parameters."""
    return ComparisonService.compare(request)
