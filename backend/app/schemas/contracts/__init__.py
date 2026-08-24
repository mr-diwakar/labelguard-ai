"""
Phase 11 integration contracts.

Typed, stable interfaces that sit AROUND the Legal Metrology core:

    INPUT  ->  INTEGRATION CONTRACTS  ->  EXISTING ENGINE  ->  ASSESSMENT

Nothing here re-implements the engine. The extraction layer speaks the richer
DetectionStatus / ExtractedDeclaration vocabulary and is mapped DOWN to the engine's
Declaration/DeclarationStatus by documented, tested adapters. Verification, nutrition,
product and evidence contracts define shapes only; their algorithms are later phases.

Import from this package rather than the submodules, e.g.:

    from app.schemas.contracts import ExtractedDeclaration, ScanResult
"""

from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.detection import (
    CONFIRMED_ABSENT_CONFIDENCE,
    ExtractedDeclaration,
    detection_to_declaration_status,
)
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.guidance import ConsumerGuidance, GuidanceItem
from app.schemas.contracts.nutrition import NutritionFacts, NutritionValue
from app.schemas.contracts.product import ProductProfile
from app.schemas.contracts.scan import ScanResult, ScanStageStatus
from app.schemas.contracts.verification import (
    MeasuredValue,
    VerificationInput,
    VerificationResult,
)

__all__ = [
    "CONFIRMED_ABSENT_CONFIDENCE",
    "ConsumerGuidance",
    "EvidenceReference",
    "ExtractedDeclaration",
    "GuidanceItem",
    "InspectionContext",
    "MeasuredValue",
    "NutritionFacts",
    "NutritionValue",
    "ProductProfile",
    "ScanResult",
    "ScanStageStatus",
    "VerificationInput",
    "VerificationResult",
    "detection_to_declaration_status",
]
