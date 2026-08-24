"""
Consumer-guidance contract (Phase 18).

Turns an automated ``ComplianceAssessment`` (and optional label-to-product
``VerificationResult`` list) into plain-language guidance a consumer can act on. It
RE-USES the existing evidence contract (``EvidenceReference``) and the existing
vocabulary (``Severity``, ``FindingKind``, ``ComplianceStatus``); it introduces no new
verdict and restates none of the legal reasoning.

Boundaries baked into these shapes (all enforced by the builder in
``app.pipeline.guidance``):
  * This is guidance about an AUTOMATED assessment. It is never a legal determination
    and never an accusation of fraud, cheating or crime.
  * LabelGuard does NOT file complaints and submits nothing to any authority. The
    ``next_steps`` describe actions the CONSUMER may choose to take; the tool performs
    none of them and claims none as done.
  * Every uncertainty the assessment surfaced -- a field OCR could not read, a value a
    camera cannot physically measure, a difference that still needs checking -- is
    carried through into ``limitations`` / ``what_is_uncertain`` rather than dropped or
    hardened into a verdict.
"""

from pydantic import Field

from app.core.enums import ComplianceStatus, FindingKind, Severity
from app.schemas.common import APIModel
from app.schemas.contracts.evidence import EvidenceReference


class GuidanceItem(APIModel):
    """
    Structured guidance for one issue worth the consumer's attention.

    Mirrors the product spec's per-issue shape -- ``issue``, ``severity``,
    ``recommended_evidence``, ``next_steps``, ``limitations`` -- and adds only honest
    provenance (``finding_kind``, ``source_reference``, ``detail``) so the item can be
    traced back to the assessment/verification it came from. ``finding_kind`` is either
    POTENTIAL_NON_COMPLIANCE or MANUAL_REVIEW; it is never a legal verdict.
    """

    issue: str
    finding_kind: FindingKind
    severity: Severity = Severity.UNSPECIFIED
    # rule_code (from the engine) or the verification field this item was derived from.
    source_reference: str | None = None
    # The engine/verification reason, carried verbatim for traceability.
    detail: str | None = None
    recommended_evidence: list[EvidenceReference] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ConsumerGuidance(APIModel):
    """
    One scan, explained to a consumer.

    The five narrative sections mirror the product spec exactly:
        what_we_found         -> WHAT WE FOUND
        why_it_matters        -> WHY IT MATTERS
        what_is_uncertain     -> WHAT IS UNCERTAIN
        what_evidence_to_keep -> WHAT EVIDENCE TO KEEP  (reuses EvidenceReference)
        what_you_can_do_next  -> WHAT YOU CAN DO NEXT

    ``status`` echoes the engine's own ``ComplianceStatus`` (never re-derived here), and
    ``items`` holds the structured per-issue guidance behind the narrative.
    """

    status: ComplianceStatus
    headline: str
    items: list[GuidanceItem] = Field(default_factory=list)
    what_we_found: list[str] = Field(default_factory=list)
    why_it_matters: list[str] = Field(default_factory=list)
    what_is_uncertain: list[str] = Field(default_factory=list)
    what_evidence_to_keep: list[EvidenceReference] = Field(default_factory=list)
    what_you_can_do_next: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str
