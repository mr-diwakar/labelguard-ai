"""
Legal-integration adapter (Phase 16).

Bridges the deterministic declaration-extraction layer (Phase 15) to the existing
Legal Metrology ``ComplianceEngine``. This is an ADAPTER, not a second engine: it
converts extraction output into the engine's ``Declaration`` input, invokes the engine
unchanged, and returns the engine's own ``ComplianceAssessment``. No legal rule is
re-implemented here and no parallel verdict vocabulary is introduced -- LabelGuard has
exactly one verdict system, and it lives in ``app.compliance``.

Distinctions this layer must preserve (all enforced by the engine it delegates to,
never overridden here):
  * OCR failure is not the same as a declaration being absent.
  * Low OCR/extraction confidence is not non-compliance -- it is manual review.
  * A field not detected in a single scan is not proof of omission.
  * "Potential non-compliance" / "manual review" are never "fraud" or a legal verdict.

The one lever that governs "not detected != omission" is ``label_readable``:
  * Extraction (Phase 15) emits only DETECTED / UNCERTAIN and never asserts a reliable
    absence, so an undetected required field is simply missing from the declaration
    list handed to the engine.
  * ``presence_outcome`` (validators/support.py) treats a missing required field as
    POTENTIAL_NON_COMPLIANCE only when ``label_readable is True`` -- an explicit,
    independent determination that the whole label was legibly captured. Otherwise the
    field is routed to MANUAL_REVIEW.
  * Therefore this adapter defaults ``label_readable`` to ``None`` (unknown) and never
    infers it from per-field OCR confidence. A caller may pass ``True`` only when a
    readability determination (e.g. the Phase 12 image-quality stage) justifies it;
    doing so is what lets a genuine omission surface, without a single OCR miss being
    mistaken for one.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from app.compliance.engine import ComplianceEngine
from app.core.enums import ProductCategory
from app.schemas.assessment import ComplianceAssessment, ComplianceRequest
from app.schemas.contracts.detection import ExtractedDeclaration
from app.schemas.declaration import Declaration
from app.schemas.extraction import ExtractionResult


def declarations_for_engine(
    extracted: Sequence[ExtractedDeclaration],
    *,
    label_readable: bool | None = None,
) -> list[Declaration]:
    """Adapt extraction-layer declarations DOWN to engine ``Declaration`` inputs.

    Uses the existing ``ExtractedDeclaration.to_declaration`` mapping (DETECTED ->
    DETECTED, UNCERTAIN -> LOW_CONFIDENCE, ...). NOT_APPLICABLE fields are dropped
    (``to_declaration`` returns ``None``) because applicability is decided per-rule by
    the resolver, not by the extractor.
    """
    declarations: list[Declaration] = []
    for item in extracted:
        declaration = item.to_declaration(label_readable=label_readable)
        if declaration is not None:
            declarations.append(declaration)
    return declarations


def assess_extraction(
    engine: ComplianceEngine,
    extraction: ExtractionResult,
    *,
    inspection_date: date | datetime,
    product_category: ProductCategory | str,
    is_imported: bool = False,
    size_is_relevant: bool | None = None,
    label_readable: bool | None = None,
) -> ComplianceAssessment:
    """Run the existing compliance engine over a Phase 15 extraction result.

    Returns the engine's own ``ComplianceAssessment`` unchanged. The extraction layer
    decides *what was read*; the engine decides *what that means legally*. This function
    only carries data across the seam -- it makes no legal judgement of its own.
    """
    declarations = declarations_for_engine(
        extraction.to_extracted_declarations(),
        label_readable=label_readable,
    )
    request = ComplianceRequest(
        inspection_date=inspection_date,
        product_category=product_category,
        is_imported=is_imported,
        size_is_relevant=size_is_relevant,
        label_readable=label_readable,
        declarations=declarations,
    )
    return engine.evaluate(request)
