from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.enums import ComplianceStatus
from app.schemas.common import MobileModel
from app.schemas.declaration import DeclarationCheck


class InspectionAssessment(MobileModel):
    status: ComplianceStatus
    confidence: float | None = Field(default=None, ge=0, le=1)
    rule_reference: str | None = Field(default=None, alias="ruleReference")
    passed: list[DeclarationCheck] = Field(default_factory=list)
    violations: list[DeclarationCheck] = Field(default_factory=list)
    manual_review: list[DeclarationCheck] = Field(default_factory=list, alias="manualReview")


class InspectionResponse(MobileModel):
    """GET /inspections/{id} body. Field names match mobile/types/inspection.ts."""

    id: UUID
    product_name: str = Field(alias="productName")
    inspected_at: datetime = Field(alias="inspectedAt")
    category: str | None = None
    assessment: InspectionAssessment
    is_demo: bool = Field(default=False, alias="isDemo")


class InspectionSummary(MobileModel):
    total: int = Field(ge=0)
    compliant: int = Field(ge=0)
    manual_review: int = Field(default=0, ge=0, alias="manualReview")
    potential_issues: int = Field(default=0, ge=0, alias="potentialIssues")


class InspectionListResponse(MobileModel):
    items: list[InspectionResponse] = Field(default_factory=list)
    summary: InspectionSummary
