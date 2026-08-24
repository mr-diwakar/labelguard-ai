"""Future POST /api/v1/scans response. The orchestrator is not implemented in this phase."""

from pydantic import Field

from app.core.enums import ReportStatus
from app.schemas.common import APIModel
from app.schemas.compliance import ComplianceResult
from app.schemas.ingredient import IngredientItem
from app.schemas.inspection import InspectionResponse
from app.schemas.nutrition import NutritionResult
from app.schemas.ocr import ImageQualityResult


class ScanResponse(APIModel):
    """
    What the mobile app will receive after a scan.

    nutrition is null and ingredients is [] when those services are unavailable.
    report_status is FAILED when PDF generation fails after the inspection is stored.
    """

    inspection: InspectionResponse
    compliance: ComplianceResult
    image_quality: ImageQualityResult | None = None
    nutrition: NutritionResult | None = None
    ingredients: list[IngredientItem] = Field(default_factory=list)
    evidence_warning: str | None = None
    report_status: ReportStatus | None = None
    warnings: list[str] = Field(default_factory=list)
