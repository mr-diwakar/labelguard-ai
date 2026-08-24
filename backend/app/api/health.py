"""Service liveness endpoint."""

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service liveness check")
def health_check() -> HealthResponse:
    """Reports that the process is up and able to serve requests."""
    return HealthResponse(status="ok")
