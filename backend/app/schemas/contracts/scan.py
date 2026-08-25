"""
Final scan result contract (Phase 11; orchestrator added in Phase 19).

The aggregate the scan orchestrator returns. Phase 11 fixed the shape so the OCR,
verification, nutrition and legal layers could be assembled without renegotiating types
later; Phase 19 adds the orchestrator (``app.pipeline.orchestrator``) that populates it,
plus two additive fields it needs -- ``guidance`` (Phase 18 consumer guidance) and
``stages`` (per-stage operational status). Both default empty, so every earlier
construction of ``ScanResult`` is unaffected.

The legal verdict is NOT restated here: legal_assessment reuses the engine's own
ComplianceAssessment. legal_assessment=None means the engine has not run or could not
run — it is never an implied COMPLIANT. nutrition=None / ingredients=[] / verification=[]
mean those layers had nothing to report, which never upgrades the legal status. A FAILED
or SKIPPED entry in ``stages`` is a coverage gap surfaced honestly, never a pass.
"""

from pydantic import Field

from app.core.enums import StageOutcome
from app.schemas.assessment import ComplianceAssessment
from app.schemas.common import APIModel
from app.schemas.contracts.context import InspectionContext
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.guidance import ConsumerGuidance
from app.schemas.contracts.nutrition import NutritionFacts
from app.schemas.contracts.product import ProductProfile
from app.schemas.contracts.verification import VerificationInput, VerificationResult
from app.schemas.ingredient import IngredientItem
from app.schemas.ocr import OCRResult


class ScanRequest(APIModel):
    """
    Input to the unified scan endpoint -- the arguments ``run_scan`` accepts, as JSON.

    Mirrors the orchestrator's parameters, minus the engine (built server-side from the
    versioned legal rules, never sent by the client). ``ocr_results`` are already-recognised
    OCR regions, not a raw image: the orchestrator consumes ``OCRResult[]`` and the
    image->OCR stage (``app.imaging.process_scan``) runs ahead of it only when an OCR
    provider is installed.

    Every field is optional with an empty/None default, so a minimal ``{}`` body is a valid
    (empty) scan and ``scan_id`` is generated when omitted. ``APIModel`` forbids unknown
    keys, so a misspelled field is a client error rather than a silently dropped input.
    """

    scan_id: str | None = None
    context: InspectionContext | None = None
    ocr_results: list[OCRResult] = Field(default_factory=list)
    verification_inputs: list[VerificationInput] = Field(default_factory=list)
    nutrition: NutritionFacts | None = None
    product: ProductProfile | None = None
    ingredients: list[IngredientItem] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ScanStageStatus(APIModel):
    """
    What one orchestration stage did, so a partial result never hides a failure.

    ``stage`` is the stage name (extraction / legal / verification / guidance /
    nutrition); ``status`` is a :class:`StageOutcome`; ``detail`` is a short,
    human-readable reason (why it was skipped, what it produced, or the error class if
    it failed). This is operational metadata only — it carries no legal meaning.
    """

    stage: str
    status: StageOutcome
    detail: str | None = None


class ScanResult(APIModel):
    """
    Everything one scan produced, assembled around the unchanged legal engine.

    Layer boundaries are explicit:
        declarations     -> extraction layer (mapped DOWN to the engine via adapters)
        legal_assessment -> the existing ComplianceEngine output (reused, not rebuilt)
        verification     -> label-to-product checks (declared vs observed; no fraud verdicts)
        guidance         -> Phase 18 consumer guidance derived from the two above
        nutrition        -> nutrition panel (missing is null, never zero)
        ingredients      -> ingredient list ([] is a valid result)
        evidence         -> pointers to supporting artefacts (no images generated here)
        stages           -> per-stage operational status (partial results stay honest)
    """

    scan_id: str
    context: InspectionContext | None = None
    product: ProductProfile | None = None
    declarations: list[ExtractedDeclaration] = Field(default_factory=list)
    legal_assessment: ComplianceAssessment | None = None
    verification: list[VerificationResult] = Field(default_factory=list)
    guidance: ConsumerGuidance | None = None
    nutrition: NutritionFacts | None = None
    ingredients: list[IngredientItem] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    stages: list[ScanStageStatus] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
