"""
Final scan result contract (Phase 11).

The aggregate a future scan orchestrator will return. The orchestrator itself is NOT
implemented in this phase — this only fixes the shape so the OCR, verification,
nutrition and legal layers can be assembled without renegotiating types later.

The legal verdict is NOT restated here: legal_assessment reuses the engine's own
ComplianceAssessment. legal_assessment=None means the engine has not run or could not
run — it is never an implied COMPLIANT. nutrition=None / ingredients=[] / verification=[]
mean those layers had nothing to report, which never upgrades the legal status.
"""

from pydantic import Field

from app.schemas.assessment import ComplianceAssessment
from app.schemas.common import APIModel
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.nutrition import NutritionFacts
from app.schemas.contracts.product import ProductProfile
from app.schemas.contracts.verification import VerificationResult
from app.schemas.ingredient import IngredientItem


class ScanResult(APIModel):
    """
    Everything one scan produced, assembled around the unchanged legal engine.

    Layer boundaries are explicit:
        declarations     -> extraction layer (mapped DOWN to the engine via adapters)
        legal_assessment -> the existing ComplianceEngine output (reused, not rebuilt)
        verification     -> label-to-product checks (declared vs observed; no fraud verdicts)
        nutrition        -> nutrition panel (missing is null, never zero)
        ingredients      -> ingredient list ([] is a valid result)
        evidence         -> pointers to supporting artefacts (no images generated here)
    """

    scan_id: str
    context: InspectionContext | None = None
    product: ProductProfile | None = None
    declarations: list[ExtractedDeclaration] = Field(default_factory=list)
    legal_assessment: ComplianceAssessment | None = None
    verification: list[VerificationResult] = Field(default_factory=list)
    nutrition: NutritionFacts | None = None
    ingredients: list[IngredientItem] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
