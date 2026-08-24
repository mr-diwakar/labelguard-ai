"""Stable contracts between the API, the legal engine and teammate modules."""

from app.schemas.applicability import ApplicabilityReport, ProductContext
from app.schemas.assessment import AssessmentItem, ComplianceAssessment, ComplianceRequest
from app.schemas.common import BoundingBox, ErrorResponse, HealthResponse
from app.schemas.compliance import ComplianceFinding, ComplianceResult
from app.schemas.declaration import Declaration, DeclarationCheck
from app.schemas.evidence import EvidenceItem
from app.schemas.ingredient import IngredientItem
from app.schemas.inspection import InspectionResponse, InspectionSummary
from app.schemas.legal_rule import LegalRuleRecord
from app.schemas.nutrition import NutritionResult
from app.schemas.ocr import ImageQualityResult, OCRResult
from app.schemas.product import ProductResponse
from app.schemas.report import ReportResult
from app.schemas.scan import ScanResponse
from app.schemas.validation import ValidationContext, ValidationEvidence, ValidationResult

__all__ = [
    "ApplicabilityReport",
    "AssessmentItem",
    "BoundingBox",
    "ComplianceAssessment",
    "ComplianceFinding",
    "ComplianceRequest",
    "ComplianceResult",
    "Declaration",
    "DeclarationCheck",
    "ErrorResponse",
    "EvidenceItem",
    "HealthResponse",
    "ImageQualityResult",
    "IngredientItem",
    "InspectionResponse",
    "InspectionSummary",
    "LegalRuleRecord",
    "NutritionResult",
    "OCRResult",
    "ProductContext",
    "ProductResponse",
    "ReportResult",
    "ScanResponse",
    "ValidationContext",
    "ValidationEvidence",
    "ValidationResult",
]
