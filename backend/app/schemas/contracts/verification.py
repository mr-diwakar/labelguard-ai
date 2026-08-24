"""
Label-to-product verification contract (Phase 11).

This defines the SHAPE of a verification check only. The verification algorithm is a
later phase and is deliberately not implemented here. A verification module can later
consume these contracts without touching ComplianceEngine.

Two principles are encoded structurally:
  * DECLARED (expected, from the label/OCR) is separate from OBSERVED (from a
    measurement or the user). A smartphone photo cannot measure mass, so an observed
    value always names its ObservationSource.
  * A missing observation is valid input and maps to COULD_NOT_VERIFY. AI verification
    never emits FRAUD / CHEATING / ILLEGAL.
"""

from pydantic import Field

from app.core.enums import ObservationSource, VerificationOutcome
from app.schemas.common import APIModel
from app.schemas.contracts.evidence import EvidenceReference


class MeasuredValue(APIModel):
    """A value with an optional unit. Used for both declared and observed values."""

    value: float
    unit: str | None = None


class VerificationInput(APIModel):
    """
    Input to a future verification check.

    Example:
        {
            "field": "net_quantity",
            "expected": {"value": 500, "unit": "g"},
            "observed": {"value": 472, "unit": "g"},
            "observation_confidence": 0.94,
            "observation_source": "USER_PROVIDED"
        }

    observed may be null: no observation is available yet -> COULD_NOT_VERIFY.
    """

    field: str
    expected: MeasuredValue
    observed: MeasuredValue | None = None
    observation_confidence: float | None = Field(default=None, ge=0, le=1)
    observation_source: ObservationSource | None = None
    expected_source_reference: str | None = None
    observed_source_reference: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)


class VerificationResult(APIModel):
    """
    Output shape of one verification check. Populated by a future verification module.

    status is a VerificationOutcome (MATCH / POTENTIAL_MISMATCH / COULD_NOT_VERIFY /
    MANUAL_REVIEW / NOT_APPLICABLE) — never a legal verdict and never FRAUD/ILLEGAL.
    applicable_rule_code links to a Legal Metrology rule only when one is encoded from
    an official source; tolerances are not invented here.
    """

    field: str
    expected: MeasuredValue
    observed: MeasuredValue | None = None
    status: VerificationOutcome
    difference: float | None = None
    observation_confidence: float | None = Field(default=None, ge=0, le=1)
    observation_source: ObservationSource | None = None
    method: str | None = None
    applicable_rule_code: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)
    note: str | None = None
