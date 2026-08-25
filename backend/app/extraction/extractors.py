"""
Per-field declaration extractors (Phase 15).

Each extractor turns OCR regions into a :class:`FieldExtraction` for ONE engine
field, using only deterministic signals: keyword anchoring, regex, unit/date
normalisation, spatial proximity between regions, and OCR confidence. There is no
LLM and no legal interpretation.

Design rules that keep the layer honest:
    * A numeric value that shows OCR letter/digit confusion ("5O") yields an
      UNCERTAIN field with BOTH the as-read and the corrected value preserved as
      candidates -- never a silent number.
    * When distinct values are found for one field, the field is UNCERTAIN and every
      candidate is kept; the extractor does not arbitrarily pick a winner.
    * Extraction confidence below the engine's uncertain band (0.6) is reported as
      UNCERTAIN, so the downstream engine routes it to manual review.
    * Fields are only emitted when candidates are found. Not emitting a field means
      "not detected in this scan", which the engine must NOT treat as proof of
      absence.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.enums import DeclarationSource, DetectionStatus
from app.extraction.normalization import (
    canonical_quantity_unit,
    contains_digit_confusion,
    correct_digit_confusion,
    is_pure_number,
    month_number,
)
from app.schemas.extraction import DeclarationCandidate, FieldExtraction

# Aligned with the engine's UNCERTAIN_CONFIDENCE_MAX (validators/support.py). Declared
# here as a local constant so the extraction layer never imports the compliance
# package; a test asserts the two stay consistent.
DETECTED_CONFIDENCE_THRESHOLD = 0.6

# Pattern weights: how much a match pattern is trusted, before OCR confidence.
_W_KEYWORD_CLEAN = 0.97
_W_PROXIMITY_CLEAN = 0.85
_W_FREETEXT = 0.90
_W_FREETEXT_PROXIMITY = 0.72
_W_DATE_CLEAN = 0.95
_W_CONFUSED_AS_READ = 0.42
_W_CONFUSED_CORRECTED = 0.50
_W_AMBIGUOUS = 0.45


@dataclass(frozen=True)
class OcrRegion:
    """One OCR region, normalised, as the extractors consume it.

    Decoupled from ``OCRResult`` so extractors are trivial to unit-test; the service
    adapts ``OCRResult`` -> ``OcrRegion`` (normalising text) at the boundary.
    """

    index: int
    text: str
    confidence: float | None = None
    bbox: list[int] | None = None

    @property
    def source_reference(self) -> str:
        return f"ocr_region_{self.index}"


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

# Word-boundary anchored so "rs"/"inr" inside words ("years", "hours") never match.
_CURRENCY = re.compile(r"(?i)(?:₹|\brs\.?|\binr)")
_SEP = " :=\t-–—."


def _confidence(ocr_confidence: float | None, pattern_weight: float) -> float:
    base = ocr_confidence if ocr_confidence is not None else 0.9
    return round(max(0.0, min(1.0, base * pattern_weight)), 4)


def _decide_status(candidates: Sequence[DeclarationCandidate]) -> DetectionStatus:
    """DETECTED only when there is a single confident reading; else UNCERTAIN."""
    distinct = {(candidate.value, candidate.unit) for candidate in candidates}
    if len(distinct) > 1:
        return DetectionStatus.UNCERTAIN
    best = max(candidates, key=lambda candidate: candidate.extraction_confidence)
    if best.extraction_confidence < DETECTED_CONFIDENCE_THRESHOLD:
        return DetectionStatus.UNCERTAIN
    return DetectionStatus.DETECTED


def _build(field: str, candidates: list[DeclarationCandidate]) -> FieldExtraction | None:
    if not candidates:
        return None
    return FieldExtraction(
        field=field,
        status=_decide_status(candidates),
        candidates=candidates,
        source=DeclarationSource.OCR,
    )


def _tail_after(text: str, match: re.Match[str]) -> str:
    return text[match.end():].strip().lstrip(_SEP).strip()


def _center(bbox: list[int]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _near_regions(anchor: OcrRegion, regions: Sequence[OcrRegion]) -> list[OcrRegion]:
    """Regions spatially close to ``anchor``: same line to the right, then below.

    Used only as a fallback when a keyword's value sits in a separate OCR region.
    Returns an empty list when boxes are unavailable, so extraction degrades to
    single-region matching rather than guessing.
    """
    if anchor.bbox is None:
        return []
    ax, ay = _center(anchor.bbox)
    anchor_height = max(anchor.bbox[3] - anchor.bbox[1], 1)
    scored: list[tuple[float, OcrRegion]] = []
    for region in regions:
        if region.index == anchor.index or region.bbox is None:
            continue
        rx, ry = _center(region.bbox)
        dx, dy = rx - ax, ry - ay
        if abs(dy) <= 0.75 * anchor_height and dx > 0:
            scored.append((abs(dx), region))
        elif 0 < dy <= 2.0 * anchor_height:
            scored.append((2.0 * anchor_height + dy + abs(dx) * 0.1, region))
    scored.sort(key=lambda item: item[0])
    return [region for _, region in scored]


def _clean_money_token(token: str) -> str:
    token = token.strip()
    token = re.sub(r"(?i)(only|/-|/)$", "", token).strip()
    return token.rstrip(".").replace(",", "")


def _leading_value_token(tail: str) -> str | None:
    tail = _CURRENCY.sub("", tail.strip(), count=1).strip().lstrip(_SEP).strip()
    if not tail:
        return None
    return tail.split()[0]


def _numeric_candidates(
    token: str,
    *,
    unit: str | None,
    region: OcrRegion,
    clean_weight: float,
) -> list[DeclarationCandidate]:
    """Turn one numeric token into candidate(s), flagging OCR confusion honestly."""
    clean = _clean_money_token(token)
    if not clean:
        return []
    if is_pure_number(clean):
        return [
            DeclarationCandidate(
                value=clean,
                unit=unit,
                extraction_confidence=_confidence(region.confidence, clean_weight),
                ocr_confidence=region.confidence,
                source_reference=region.source_reference,
                bbox=region.bbox,
                raw_text=region.text,
            )
        ]
    if contains_digit_confusion(clean):
        corrected = _clean_money_token(correct_digit_confusion(clean))
        candidates = [
            DeclarationCandidate(
                value=clean,
                unit=unit,
                extraction_confidence=_confidence(region.confidence, _W_CONFUSED_AS_READ),
                ocr_confidence=region.confidence,
                source_reference=region.source_reference,
                bbox=region.bbox,
                raw_text=region.text,
                note="ocr_confusion:as_read",
            )
        ]
        if is_pure_number(corrected) and corrected != clean:
            candidates.append(
                DeclarationCandidate(
                    value=corrected,
                    unit=unit,
                    extraction_confidence=_confidence(region.confidence, _W_CONFUSED_CORRECTED),
                    ocr_confidence=region.confidence,
                    source_reference=region.source_reference,
                    bbox=region.bbox,
                    raw_text=region.text,
                    note="ocr_confusion:corrected",
                )
            )
        return candidates
    return []


# --------------------------------------------------------------------------- #
# Numeric declarations
# --------------------------------------------------------------------------- #

_MRP_KEYWORD = re.compile(
    r"(?i)(?:m\.?\s?r\.?\s?p\.?|maximum\s+retail\s+price|retail\s+sale\s+price|"
    r"retail\s+price|मूल्य|एमआरपी)"
)


def extract_mrp(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    candidates: list[DeclarationCandidate] = []
    for region in regions:
        keyword = _MRP_KEYWORD.search(region.text)
        currency = _CURRENCY.search(region.text)
        anchor = keyword or currency
        if anchor is None:
            continue
        has_currency = currency is not None
        token = _leading_value_token(_tail_after(region.text, anchor))
        if token is not None:
            found = _numeric_candidates(
                token,
                unit="INR" if has_currency else None,
                region=region,
                clean_weight=_W_KEYWORD_CLEAN,
            )
            if found:
                candidates.extend(found)
                continue
        # Value not in the keyword's own region: look at spatially near regions.
        for neighbour in _near_regions(region, regions):
            neighbour_currency = _CURRENCY.search(neighbour.text) is not None
            token = _leading_value_token(neighbour.text)
            if token is None:
                continue
            found = _numeric_candidates(
                token,
                unit="INR" if (has_currency or neighbour_currency) else None,
                region=neighbour,
                clean_weight=_W_PROXIMITY_CLEAN,
            )
            if found:
                candidates.extend(found)
                break
    return _build("mrp", _dedupe(candidates))


_NETQ_KEYWORD = re.compile(
    r"(?i)net\s*(?:qty\.?|quantity|wt\.?|weight|content[s]?|vol\.?|volume)"
)
# NOTE: case-sensitive on purpose. The number class admits common OCR confusables
# (O, I, l, S, B, Z), but under (?i) it would also match lowercase o/i/s/l/b/z and so
# latch onto ordinary words like "Quantity". The unit group lists both cases explicitly.
_QTY_TOKEN = re.compile(r"([0-9OIlSBZ][0-9OIlSBZ.,]*)\s*([A-Za-zµ]+)\.?")


def _quantity_candidates(
    text: str, region: OcrRegion, weight: float
) -> list[DeclarationCandidate]:
    """First real quantity token in ``text`` -> candidate(s).

    The number class also admits OCR confusables (O, I, l, S, B, Z), so it can latch
    onto ordinary words. We scan every match and skip any whose number token is neither
    a pure number nor a digit-confusion, so a keyword cannot masquerade as a value.
    """
    for match in _QTY_TOKEN.finditer(text):
        number, raw_unit = match.group(1), match.group(2)
        clean = _clean_money_token(number)
        if not clean:
            continue
        pure = is_pure_number(clean)
        confused = contains_digit_confusion(clean)
        if not (pure or confused):
            continue  # letters caught by the confusable class -- not a number
        unit = canonical_quantity_unit(raw_unit)
        if unit is None:
            # A number with an unrecognised unit: keep as a low-confidence candidate so
            # the engine routes it to manual review rather than a false finding.
            return [
                DeclarationCandidate(
                    value=f"{clean} {raw_unit}".strip(),
                    unit=raw_unit,
                    extraction_confidence=_confidence(region.confidence, _W_AMBIGUOUS),
                    ocr_confidence=region.confidence,
                    source_reference=region.source_reference,
                    bbox=region.bbox,
                    raw_text=region.text,
                    note="unrecognised_unit",
                )
            ]
        if pure:
            return [
                DeclarationCandidate(
                    value=f"{clean} {unit}",
                    unit=unit,
                    extraction_confidence=_confidence(region.confidence, weight),
                    ocr_confidence=region.confidence,
                    source_reference=region.source_reference,
                    bbox=region.bbox,
                    raw_text=region.text,
                )
            ]
        # confused: keep the as-read value and, if it corrects to a clean number, the
        # corrected value too -- distinct values make the field UNCERTAIN downstream.
        candidates = [
            DeclarationCandidate(
                value=f"{clean} {unit}",
                unit=unit,
                extraction_confidence=_confidence(region.confidence, _W_CONFUSED_AS_READ),
                ocr_confidence=region.confidence,
                source_reference=region.source_reference,
                bbox=region.bbox,
                raw_text=region.text,
                note="ocr_confusion:as_read",
            )
        ]
        corrected = _clean_money_token(correct_digit_confusion(clean))
        if is_pure_number(corrected) and corrected != clean:
            candidates.append(
                DeclarationCandidate(
                    value=f"{corrected} {unit}",
                    unit=unit,
                    extraction_confidence=_confidence(region.confidence, _W_CONFUSED_CORRECTED),
                    ocr_confidence=region.confidence,
                    source_reference=region.source_reference,
                    bbox=region.bbox,
                    raw_text=region.text,
                    note="ocr_confusion:corrected",
                )
            )
        return candidates
    return []


def extract_net_quantity(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    candidates: list[DeclarationCandidate] = []
    for region in regions:
        if _NETQ_KEYWORD.search(region.text) is None:
            continue
        found = _quantity_candidates(region.text, region, _W_KEYWORD_CLEAN)
        if found:
            candidates.extend(found)
            continue
        for neighbour in _near_regions(region, regions):
            found = _quantity_candidates(neighbour.text, neighbour, _W_PROXIMITY_CLEAN)
            if found:
                candidates.extend(found)
                break
    return _build("net_quantity", _dedupe(candidates))


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #

_MFG_KEYWORD = re.compile(
    r"(?i)(?:date\s+of\s+(?:mfg|manufacture)|mfg\.?|mfd\.?|manufactured|manufacture)"
)
_PKD_KEYWORD = re.compile(r"(?i)(?:date\s+of\s+packing|packed|packing|pkd\.?)")
_IMPORT_KEYWORD = re.compile(r"(?i)(?:date\s+of\s+import|imported\s+on)")

_DATE_NUMERIC = re.compile(
    r"\b(\d{4}-\d{1,2}(?:-\d{1,2})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4}|\d{4}/\d{1,2})\b"
)
_DATE_MONTHNAME = re.compile(r"(?i)\b(?:(\d{1,2})\s+)?([A-Za-z]{3,9})[\s,.]+(\d{2,4})\b")


def _normalise_numeric_date(raw: str) -> tuple[str | None, bool]:
    """Return (value, ambiguous?).

    A confident 4-digit-year date is normalised to the engine's canonical form and
    ``ambiguous`` is False. A two-digit year is genuinely ambiguous (century is a
    guess): the raw token is returned with ``ambiguous`` True so the field is emitted
    as UNCERTAIN rather than silently dropped or falsely normalised.
    """
    parts = re.split(r"[/-]", raw)
    if len(parts) == 3:
        a, b, c = parts
        if len(a) == 4:  # YYYY-MM-DD
            return f"{a}-{int(b):02d}-{int(c):02d}", False
        if len(c) == 4:  # DD/MM/YYYY (Indian order, as the engine reads it)
            return f"{int(a):02d}/{int(b):02d}/{c}", False
        return raw, True  # two-digit year: century is a guess -> UNCERTAIN
    if len(parts) == 2:
        a, b = parts
        if len(a) == 4:  # YYYY-MM or YYYY/MM
            return f"{a}-{int(b):02d}", False
        if len(b) == 4:  # MM/YYYY
            return f"{int(a):02d}/{b}", False
        return raw, True  # two-digit year: century is a guess -> UNCERTAIN
    return None, True


def _date_field_and_candidates(
    regions: Sequence[OcrRegion], keyword: re.Pattern[str], field: str
) -> FieldExtraction | None:
    candidates: list[DeclarationCandidate] = []
    for region in regions:
        anchor = keyword.search(region.text)
        if anchor is None:
            continue
        tail = _tail_after(region.text, anchor)
        search_texts = [tail] + [n.text for n in _near_regions(region, regions)[:2]]
        for order, text in enumerate(search_texts):
            weight = _W_DATE_CLEAN if order == 0 else _W_FREETEXT_PROXIMITY
            candidate = _extract_one_date(text, region, weight)
            if candidate is not None:
                candidates.append(candidate)
                break
    return _build(field, _dedupe(candidates))


def _extract_one_date(text: str, region: OcrRegion, weight: float) -> DeclarationCandidate | None:
    numeric = _DATE_NUMERIC.search(text)
    if numeric is not None:
        value, ambiguous = _normalise_numeric_date(numeric.group(1))
        if value is not None:
            return DeclarationCandidate(
                value=value,
                extraction_confidence=_confidence(
                    region.confidence, _W_AMBIGUOUS if ambiguous else weight
                ),
                ocr_confidence=region.confidence,
                source_reference=region.source_reference,
                bbox=region.bbox,
                raw_text=region.text,
                note="ambiguous_year" if ambiguous else None,
            )
    named = _DATE_MONTHNAME.search(text)
    if named is not None:
        day, month_name, year = named.group(1), named.group(2), named.group(3)
        month = month_number(month_name)
        if month is not None and len(year) == 4:
            value = f"{int(day):02d}/{month:02d}/{year}" if day else f"{month:02d}/{year}"
            return DeclarationCandidate(
                value=value,
                extraction_confidence=_confidence(region.confidence, weight),
                ocr_confidence=region.confidence,
                source_reference=region.source_reference,
                bbox=region.bbox,
                raw_text=region.text,
            )
    return None


def extract_manufacture_date(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    return _date_field_and_candidates(regions, _MFG_KEYWORD, "manufacture_date")


def extract_packing_date(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    return _date_field_and_candidates(regions, _PKD_KEYWORD, "packing_date")


def extract_import_date(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    return _date_field_and_candidates(regions, _IMPORT_KEYWORD, "import_date")


# --------------------------------------------------------------------------- #
# Free-text declarations
# --------------------------------------------------------------------------- #

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")


def _freetext_field(
    regions: Sequence[OcrRegion],
    keyword: re.Pattern[str],
    field: str,
    *,
    min_length: int = 2,
    max_length: int = 160,
) -> FieldExtraction | None:
    candidates: list[DeclarationCandidate] = []
    for region in regions:
        anchor = keyword.search(region.text)
        if anchor is None:
            continue
        tail = _tail_after(region.text, anchor)
        if len(tail) >= min_length:
            candidates.append(
                _freetext_candidate(tail[:max_length], region, _W_FREETEXT)
            )
            continue
        for neighbour in _near_regions(region, regions)[:1]:
            if len(neighbour.text) >= min_length:
                candidates.append(
                    _freetext_candidate(
                        neighbour.text[:max_length], neighbour, _W_FREETEXT_PROXIMITY
                    )
                )
                break
    return _build(field, _dedupe(candidates))


def _freetext_candidate(value: str, region: OcrRegion, weight: float) -> DeclarationCandidate:
    return DeclarationCandidate(
        value=value.strip(),
        extraction_confidence=_confidence(region.confidence, weight),
        ocr_confidence=region.confidence,
        source_reference=region.source_reference,
        bbox=region.bbox,
        raw_text=region.text,
    )


_MFR_KEYWORD = re.compile(r"(?i)(?:manufactured\s+by|mfd\.?\s+by|marketed\s+by|manufacturer)")
_PACKER_KEYWORD = re.compile(r"(?i)(?:packed\s+by|packer)")


def extract_manufacturer(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    result = _freetext_field(regions, _MFR_KEYWORD, "manufacturer")
    if result is not None:
        return result
    return _freetext_field(regions, _PACKER_KEYWORD, "packer")


_CARE_KEYWORD = re.compile(
    r"(?i)(?:consumer\s+care|customer\s+care|consumer\s+complaint|helpline|"
    r"toll[\s-]*free|for\s+complaints?|care\s+no\.?)"
)


def extract_consumer_care(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    candidates: list[DeclarationCandidate] = []
    for region in regions:
        if _CARE_KEYWORD.search(region.text) is None:
            continue
        contact = _EMAIL.search(region.text) or _PHONE.search(region.text)
        search_regions = [region] + _near_regions(region, regions)[:2]
        if contact is None:
            for neighbour in search_regions[1:]:
                contact = _EMAIL.search(neighbour.text) or _PHONE.search(neighbour.text)
                if contact is not None:
                    candidates.append(
                        _freetext_candidate(contact.group(0), neighbour, _W_PROXIMITY_CLEAN)
                    )
                    break
            else:
                anchor = _CARE_KEYWORD.search(region.text)
                tail = _tail_after(region.text, anchor) if anchor else ""
                if len(tail) >= 3:
                    candidates.append(_freetext_candidate(tail, region, _W_AMBIGUOUS))
        else:
            candidates.append(_freetext_candidate(contact.group(0), region, _W_FREETEXT))
    return _build("consumer_care", _dedupe(candidates))


_ORIGIN_KEYWORD = re.compile(
    r"(?i)(?:country\s+of\s+origin|made\s+in|product\s+of|imported\s+from)"
)


def extract_country_of_origin(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    return _freetext_field(regions, _ORIGIN_KEYWORD, "country_of_origin", max_length=60)


_NAME_KEYWORD = re.compile(
    r"(?i)(?:name\s+of\s+(?:commodity|product)|commodity\s+name|product\s+name|name)\s*[:\-]"
)


def extract_commodity_name(regions: Sequence[OcrRegion]) -> FieldExtraction | None:
    # Only extracted from an explicit "Name:" style label -- guessing the product
    # name from arbitrary label text would be unreliable, so we stay conservative.
    return _freetext_field(regions, _NAME_KEYWORD, "commodity_name")


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def _dedupe(candidates: list[DeclarationCandidate]) -> list[DeclarationCandidate]:
    """Collapse identical (value, unit) readings, keeping the most confident one."""
    best: dict[tuple[str | None, str | None], DeclarationCandidate] = {}
    for candidate in candidates:
        key = (candidate.value, candidate.unit)
        current = best.get(key)
        if current is None or candidate.extraction_confidence > current.extraction_confidence:
            best[key] = candidate
    return list(best.values())


# Ordered so the extracted-declaration output is stable across runs.
FIELD_EXTRACTORS = (
    extract_commodity_name,
    extract_net_quantity,
    extract_mrp,
    extract_manufacturer,
    extract_manufacture_date,
    extract_packing_date,
    extract_import_date,
    extract_consumer_care,
    extract_country_of_origin,
)


def run_extractors(regions: Sequence[OcrRegion]) -> list[FieldExtraction]:
    """Run every field extractor over the regions, dropping fields with no candidates."""
    results: list[FieldExtraction] = []
    for extractor in FIELD_EXTRACTORS:
        extraction = extractor(regions)
        if extraction is not None:
            results.append(extraction)
    return results
