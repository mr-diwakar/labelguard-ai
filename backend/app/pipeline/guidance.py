"""
Consumer guidance (Phase 18).

Assembles the ``ConsumerGuidance`` narrative from an existing ``ComplianceAssessment``
(and optional label-to-product ``VerificationResult`` list). This is a PRESENTATION
layer: it re-reads verdicts the engine and the verification layer already produced and
explains them for a consumer. It computes no new verdict, invents no severity, and
never contradicts the assessment's ``status``.

What it guarantees, by construction:
  * WHAT WE FOUND / WHY IT MATTERS / WHAT IS UNCERTAIN / WHAT EVIDENCE TO KEEP /
    WHAT YOU CAN DO NEXT are always populated coherently, including the all-clear case.
  * A MANUAL_REVIEW or COULD_NOT_VERIFY outcome is reported as uncertainty to resolve,
    never as a problem found; a POTENTIAL_MISMATCH is a difference to check, never fraud.
  * The physical-quantity caveat and every ``note`` the verification layer attached are
    carried into ``limitations`` verbatim -- nothing is silently dropped.
  * ``next_steps`` are consumer-owned. Nothing here contacts a seller or an authority,
    and the disclaimer states plainly that LabelGuard has filed nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.enums import (
    ComplianceStatus,
    EvidenceType,
    FindingKind,
    Severity,
    VerificationOutcome,
)
from app.schemas.assessment import AssessmentItem, ComplianceAssessment
from app.schemas.contracts.evidence import EvidenceReference
from app.schemas.contracts.guidance import ConsumerGuidance, GuidanceItem
from app.schemas.contracts.verification import VerificationResult
from app.schemas.validation import ValidationEvidence

DISCLAIMER = (
    "This is an automated assessment meant to help you decide what to check -- it is not "
    "a legal determination and not an accusation. LabelGuard has not contacted any seller "
    "or authority and has not filed any complaint; any next step is yours to take."
)

# Global limitations that apply to every scan, independent of the specific findings.
_BASE_LIMITATIONS = (
    "These conclusions come from automated reading of a single set of photos; they can be wrong.",
    "A field we could not read is not the same as a field that is missing from the label.",
    "Low reading confidence means 'unconfirmed', not 'non-compliant'.",
)

# Consumer-owned actions. LabelGuard performs none of these; they are suggestions only.
_BASE_NEXT_STEPS = (
    "Keep the evidence listed above until the matter is settled.",
    "Re-check the printed label yourself in good light, especially any value flagged below.",
    "You can raise a concern with the seller or shop where you bought the product.",
    "If you still have a concern, you may choose to report it yourself to the Legal "
    "Metrology department in your state. LabelGuard does not report anything on your "
    "behalf and has filed no complaint.",
)

_HEADLINES = {
    ComplianceStatus.COMPLIANT: "The automated checks did not flag any issue on this label.",
    ComplianceStatus.POTENTIAL_NON_COMPLIANCE: "We found something on this label worth checking.",
    ComplianceStatus.MANUAL_REVIEW: "Some details could not be confirmed automatically and need a closer look.",
}


def _safe_bbox(bbox: list[int] | None) -> list[int] | None:
    """Pass a pixel bbox through only if it is well-formed and ordered.

    ``EvidenceReference`` requires ``[x1, y1, x2, y2]`` with ``x2 >= x1`` and
    ``y2 >= y1``; upstream ``ValidationEvidence`` carries no such guarantee, so an
    ill-formed box is dropped rather than allowed to raise mid-build.
    """
    if not bbox or len(bbox) != 4:
        return None
    x1, y1, x2, y2 = bbox
    if x2 < x1 or y2 < y1:
        return None
    return list(bbox)


def _evidence_from_validation(ev: ValidationEvidence, index: int) -> EvidenceReference:
    """Adapt an engine ``ValidationEvidence`` snapshot into an ``EvidenceReference``."""
    reading = f": “{ev.value}”" if ev.value else ""
    return EvidenceReference(
        evidence_id=f"decl_{ev.field}_{index}",
        evidence_type=EvidenceType.OCR_REGION,
        source=ev.source,
        bbox=_safe_bbox(ev.bbox),
        confidence=ev.confidence,
        note=f"What the scan read for {ev.field}{reading}.",
    )


def _baseline_evidence() -> list[EvidenceReference]:
    """The artefacts a consumer should retain regardless of the specific finding."""
    return [
        EvidenceReference(
            evidence_id="keep_product_photo",
            evidence_type=EvidenceType.PRODUCT_IMAGE,
            note=(
                "Keep the original photo of the label -- the front of the pack and the panel "
                "showing MRP, net quantity and dates -- taken close up and in good light."
            ),
        ),
        EvidenceReference(
            evidence_id="keep_proof_of_purchase",
            evidence_type=EvidenceType.DOCUMENT,
            note="Keep the receipt or invoice showing what you paid and where you bought it.",
        ),
        EvidenceReference(
            evidence_id="keep_packaging",
            evidence_type=EvidenceType.OTHER,
            note=(
                "Keep the packaging itself until the matter is resolved, in case the printed "
                "declarations need to be re-checked."
            ),
        ),
    ]


def _dedupe_evidence(refs: Sequence[EvidenceReference]) -> list[EvidenceReference]:
    seen: set[str] = set()
    out: list[EvidenceReference] = []
    for ref in refs:
        if ref.evidence_id in seen:
            continue
        seen.add(ref.evidence_id)
        out.append(ref)
    return out


def _dedupe_str(lines: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def _label_for(item: AssessmentItem) -> str:
    """A human name for the requirement behind an assessment item."""
    return item.rule_name or item.rule_code


def _violation_item(item: AssessmentItem) -> GuidanceItem:
    evidence = [_evidence_from_validation(ev, i) for i, ev in enumerate(item.evidence)]
    return GuidanceItem(
        issue=f"The label may not meet the requirement: {_label_for(item)}.",
        finding_kind=FindingKind.POTENTIAL_NON_COMPLIANCE,
        severity=item.severity,
        source_reference=item.rule_code,
        detail=item.reason,
        recommended_evidence=evidence,
        next_steps=_dedupe_str(
            [step for step in [item.recommended_action] if step] + list(_BASE_NEXT_STEPS)
        ),
        limitations=[
            "This is a potential issue raised by automated checks, not a proven violation. "
            "Only the Legal Metrology authority can make a legal determination.",
        ],
    )


def _manual_review_item(item: AssessmentItem) -> GuidanceItem:
    evidence = [_evidence_from_validation(ev, i) for i, ev in enumerate(item.evidence)]
    return GuidanceItem(
        issue=f"We could not automatically confirm: {_label_for(item)}.",
        finding_kind=FindingKind.MANUAL_REVIEW,
        severity=item.severity,
        source_reference=item.rule_code,
        detail=item.reason,
        recommended_evidence=evidence,
        next_steps=_dedupe_str(
            [step for step in [item.recommended_action] if step]
            + ["Re-scan the label straight-on, close up and in good light, then check this value yourself."]
        ),
        limitations=[
            "This is unconfirmed, not a problem found. It usually means the label could not "
            "be read clearly, which is not the same as a declaration being absent.",
        ],
    )


# Verification outcomes -> how the consumer should read them. MATCH / NOT_APPLICABLE do
# not become guidance items (nothing for the consumer to act on).
def _verification_item(result: VerificationResult) -> GuidanceItem | None:
    field = result.field
    note = result.note or ""
    limitations = [note] if note else []
    if result.status is VerificationOutcome.POTENTIAL_MISMATCH:
        issue = (
            f"The {field} visible in the photo looks different from the {field} declared on "
            "the label."
        )
        next_steps = [
            f"Look at the {field} on the actual product again and compare it with the label.",
        ]
    elif result.status is VerificationOutcome.COULD_NOT_VERIFY:
        issue = f"We could not cross-check the {field} from the photo."
        next_steps = [
            f"Take a clearer, straight-on photo where the {field} is fully visible, then compare it yourself.",
        ]
    elif result.status is VerificationOutcome.MANUAL_REVIEW:
        issue = f"The {field} needs a person to compare it against the label."
        next_steps = [
            f"Check the {field} on the product against the label yourself.",
        ]
    else:  # MATCH / NOT_APPLICABLE -> not surfaced
        return None

    return GuidanceItem(
        issue=issue,
        finding_kind=FindingKind.MANUAL_REVIEW,
        severity=Severity.UNSPECIFIED,  # a photo comparison is not ranked in severity
        source_reference=field,
        detail=note or None,
        recommended_evidence=list(result.evidence),
        next_steps=next_steps,
        limitations=limitations,
    )


def build_guidance(
    assessment: ComplianceAssessment,
    verification: Sequence[VerificationResult] = (),
    *,
    evidence: Sequence[EvidenceReference] = (),
) -> ConsumerGuidance:
    """Build consumer guidance from an assessment and optional verification results.

    ``assessment`` is the engine's own output; its ``status`` is echoed, never
    recomputed. ``verification`` are label-to-product checks (Phase 17). ``evidence`` is
    any evidence already gathered in the scan (e.g. OCR regions) to also recommend
    keeping. Nothing here changes the verdict or takes any action on the consumer's
    behalf.
    """
    items: list[GuidanceItem] = []
    items.extend(_violation_item(item) for item in assessment.violations)
    items.extend(_manual_review_item(item) for item in assessment.manual_review)
    items.extend(filter(None, (_verification_item(r) for r in verification)))

    problems = [it for it in items if it.finding_kind is FindingKind.POTENTIAL_NON_COMPLIANCE]
    uncertainties = [it for it in items if it.finding_kind is FindingKind.MANUAL_REVIEW]

    # WHAT WE FOUND
    what_we_found: list[str] = []
    if problems:
        what_we_found.append(
            f"{len(problems)} thing(s) on the label may not meet labelling requirements."
        )
    if uncertainties:
        what_we_found.append(
            f"{len(uncertainties)} thing(s) could not be confirmed automatically."
        )
    passed_count = assessment.passed_count
    if passed_count:
        what_we_found.append(
            f"{passed_count} required declaration(s) were read and looked present."
        )
    if not problems and not uncertainties:
        what_we_found.append(
            "No labelling issue was flagged by the automated checks on the photos you provided."
        )
    what_we_found.extend(it.issue for it in items)

    # WHY IT MATTERS
    why_it_matters: list[str] = []
    if problems:
        why_it_matters.append(
            "Mandatory declarations such as price, net quantity, dates and the maker's "
            "details exist so you can buy informed and not be short-changed; a label that "
            "may miss one is worth checking before you rely on it."
        )
    if uncertainties and not problems:
        why_it_matters.append(
            "The items below are unconfirmed rather than wrong -- worth a second look so a "
            "genuine issue is not missed and a good label is not wrongly doubted."
        )
    if not problems and not uncertainties:
        why_it_matters.append(
            "Nothing needs action right now; this note is only so you know what was and was "
            "not checked."
        )

    # WHAT IS UNCERTAIN
    what_is_uncertain = [it.issue for it in uncertainties]
    if problems:
        what_is_uncertain.append(
            "A potential issue is not a proven one -- only the Legal Metrology authority can "
            "make a legal determination."
        )

    # WHAT EVIDENCE TO KEEP
    keep = _dedupe_evidence(
        list(evidence)
        + [ref for it in items for ref in it.recommended_evidence]
        + _baseline_evidence()
    )

    # WHAT YOU CAN DO NEXT
    next_steps = _dedupe_str(
        [step for it in items for step in it.next_steps] + list(_BASE_NEXT_STEPS)
    )

    # LIMITATIONS -- global caveats plus every note the layers attached, none dropped.
    limitations = _dedupe_str(
        list(_BASE_LIMITATIONS)
        + [lim for it in items for lim in it.limitations]
        + list(assessment.warnings)
    )

    return ConsumerGuidance(
        status=assessment.status,
        headline=_HEADLINES.get(assessment.status, _HEADLINES[ComplianceStatus.MANUAL_REVIEW]),
        items=items,
        what_we_found=_dedupe_str(what_we_found),
        why_it_matters=_dedupe_str(why_it_matters),
        what_is_uncertain=_dedupe_str(what_is_uncertain),
        what_evidence_to_keep=keep,
        what_you_can_do_next=next_steps,
        limitations=limitations,
        disclaimer=DISCLAIMER,
    )
