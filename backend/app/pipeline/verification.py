"""
Label-to-product verification (Phase 17).

Compares a value DECLARED on the label (extracted in Phase 15) against a value
OBSERVED in the SAME captured product image. The current image is the ONLY evidence
source: there is no lookup against external databases, marketplaces, or the web.

Hard constraints, all encoded below:
  * The result vocabulary is the EXISTING ``VerificationOutcome`` on the EXISTING
    ``VerificationResult`` contract. Nothing here ever emits "fraud", "counterfeit" or
    a legal verdict -- a difference is a POTENTIAL_MISMATCH to verify, no more.
        MATCH               -> VerificationOutcome.MATCH
        POSSIBLE_DIFFERENCE -> VerificationOutcome.POTENTIAL_MISMATCH
        UNCERTAIN           -> VerificationOutcome.MANUAL_REVIEW
        INSUFFICIENT_IMAGE  -> VerificationOutcome.COULD_NOT_VERIFY
  * Image capture conditions (rotation, scale, lighting, blur, compression, distance)
    must NOT manufacture a mismatch. They arrive as a low ``observation_confidence``;
    below the threshold the check is COULD_NOT_VERIFY, never POTENTIAL_MISMATCH.
  * No numeric tolerance is invented (the contract forbids it). Two PRINTED values are
    compared for equality after reconciling comparable units; any real difference is
    reported as a possible difference with the raw ``difference`` for transparency.
  * PHYSICAL QUANTITY LIMITATION: a camera cannot measure the actual mass or volume of
    the contents. For quantity fields the comparison is declared-printed vs
    visible-printed only, and every such result says so.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.core.enums import VerificationOutcome
from app.schemas.contracts.verification import (
    MeasuredValue,
    VerificationInput,
    VerificationResult,
)

# Below this, a value read from the image is too unreliable (blur/distance/lighting/
# rotation/compression) to assert either a match or a difference.
OBSERVATION_CONFIDENCE_MIN = 0.6

# Fields whose values are physical quantities a photograph cannot actually measure.
PHYSICAL_QUANTITY_FIELDS = frozenset({"net_quantity"})

PHYSICAL_QUANTITY_NOTE = (
    "A photograph cannot measure the actual physical weight or volume of the contents; "
    "this only compares the declared printed quantity against a quantity visible in the "
    "image. Confirming the true contents needs a calibrated measurement."
)

_NUMERIC = re.compile(r"-?\d+(?:\.\d+)?")
_MASS = {"g": 1.0, "kg": 1000.0, "mg": 0.001}
_VOLUME = {"ml": 1.0, "l": 1000.0}


def measured_value_from_text(value: str | None, unit: str | None = None) -> MeasuredValue | None:
    """Parse an extracted string (e.g. ``"500 g"``) into a numeric ``MeasuredValue``.

    Returns ``None`` when there is no numeric value to compare (verification on this
    contract is numeric; text fields such as name are out of scope). The unit is taken
    from ``unit`` when given, else from any trailing token after the number.
    """
    if value is None:
        return None
    match = _NUMERIC.search(value)
    if match is None:
        return None
    resolved_unit = unit
    if resolved_unit is None:
        tail = value[match.end():].strip()
        resolved_unit = tail or None
    return MeasuredValue(value=float(match.group(0)), unit=resolved_unit)


def _convert_factor(from_unit: str | None, to_unit: str | None) -> float | None:
    """Multiplier to express a value given in ``from_unit`` in ``to_unit``.

    Returns ``None`` when the units are not comparable (different dimensions, or a unit
    is missing on only one side), so the caller routes to MANUAL_REVIEW rather than
    guessing a conversion.
    """
    if from_unit == to_unit:
        return 1.0
    if from_unit is None or to_unit is None:
        return None
    fu, tu = from_unit.lower(), to_unit.lower()
    if fu == tu:
        return 1.0
    for table in (_MASS, _VOLUME):
        if fu in table and tu in table:
            return table[fu] / table[tu]
    return None


def _values_equal(a: float, b: float) -> bool:
    # Float-representation hygiene only -- NOT a legal/measurement tolerance.
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def verify_one(vi: VerificationInput) -> VerificationResult:
    """Verify one declared value against one value observed in the product image."""
    is_physical = vi.field.lower() in PHYSICAL_QUANTITY_FIELDS

    def build(
        status: VerificationOutcome,
        *,
        method: str,
        note: str,
        difference: float | None = None,
    ) -> VerificationResult:
        full_note = f"{note} {PHYSICAL_QUANTITY_NOTE}" if is_physical else note
        return VerificationResult(
            field=vi.field,
            expected=vi.expected,
            observed=vi.observed,
            status=status,
            difference=difference,
            observation_confidence=vi.observation_confidence,
            observation_source=vi.observation_source,
            method=method,
            applicable_rule_code=None,
            evidence=list(vi.evidence),
            note=full_note,
        )

    if vi.observed is None:
        return build(
            VerificationOutcome.COULD_NOT_VERIFY,
            method="no_observation",
            note="No comparable value was visible in the product image, so the declared value could not be cross-checked from the image alone.",
        )

    if vi.observation_confidence is not None and vi.observation_confidence < OBSERVATION_CONFIDENCE_MIN:
        return build(
            VerificationOutcome.COULD_NOT_VERIFY,
            method="insufficient_image",
            note="The value read from the image was too low-confidence (e.g. blur, distance, lighting, rotation, or compression) to confirm either a match or a difference.",
        )

    factor = _convert_factor(vi.observed.unit, vi.expected.unit)
    if factor is None:
        return build(
            VerificationOutcome.MANUAL_REVIEW,
            method="uncertain_units",
            note="The declared and observed values use units that cannot be compared automatically; a person should check them.",
        )

    observed_value = vi.observed.value * factor
    if _values_equal(observed_value, vi.expected.value):
        return build(
            VerificationOutcome.MATCH,
            method="image_consistency_check",
            note="The value visible in the image matches the declared value.",
            difference=0.0,
        )

    return build(
        VerificationOutcome.POTENTIAL_MISMATCH,
        method="image_consistency_check",
        note="The value visible in the image differs from the declared value. This is a possible difference to verify, not a determination of wrongdoing.",
        difference=round(observed_value - vi.expected.value, 6),
    )


def verify(inputs: Sequence[VerificationInput]) -> list[VerificationResult]:
    """Verify each declared/observed pair. Order is preserved for stable output."""
    return [verify_one(item) for item in inputs]
