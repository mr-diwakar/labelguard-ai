# LabelGuard AI — Declaration Extraction (Phase 15)

**Status:** `[IMPLEMENTED]` — deterministic extraction of structured Legal Metrology
declarations from OCR regions, with candidate preservation, explicit uncertainty, and
a tested adapter DOWN to the Phase 11 `ExtractedDeclaration` contract.
**Not in this phase:** any Legal Metrology assessment (Phase 16), label-to-image
verification (Phase 17), consumer guidance (Phase 18), scan orchestration (Phase 19),
LLM/NLP inference, external lookups, or a public API.

This document describes the pipeline segment that sits strictly **between OCR and the
legal engine**:

```text
OCRResult[] → normalise → per-field extractors → ExtractionResult → (adapt DOWN) → ExtractedDeclaration[]
```

The guiding invariant: **extraction decides *what a region says*, never *what it means
legally*.** It reads characters into candidate field values; it never asserts that a
declaration is absent, never rewrites an ambiguous number silently, and never produces a
compliance verdict.

---

## 1. Architectural position

Extraction is a distinct layer from OCR (which recognises characters) and from the
engine (which judges compliance). It consumes the Phase 11 `OCRResult` contract and
produces the Phase 11 `ExtractedDeclaration` contract via a richer intermediate model:

```text
 OCRResult[] ──▶ DeclarationExtractor.extract ──▶ ExtractionResult ──▶ ExtractedDeclaration[]
 (Phase 11)      (normalise + run extractors)     (candidates kept)     (Phase 11, engine input)
```

New package, mirroring the existing `app/compliance/` and `app/imaging/` layout:

- `app/extraction/normalization.py` — pure text helpers (NFKC, Devanagari digits,
  OCR-confusion detection, unit/month canonicalisation). No I/O, no legal logic.
- `app/extraction/extractors.py` — one deterministic extractor per engine field.
- `app/extraction/service.py` — `DeclarationExtractor` / `extract_declarations`, the
  entry point that adapts `OCRResult → OcrRegion` and runs the extractors.
- `app/schemas/extraction.py` — the rich contracts `DeclarationCandidate` /
  `FieldExtraction` / `ExtractionResult`, which adapt DOWN to `ExtractedDeclaration`.

The layer imports **schemas + enums only**; it never imports `app.compliance`, so it can
be replaced without touching Legal Metrology logic.

## 2. The internal service (not a public API)

```python
from app.extraction import extract_declarations

result = extract_declarations(ocr_results)          # ocr_results: Sequence[OCRResult]
declarations = result.to_extracted_declarations()   # list[ExtractedDeclaration] for the engine
```

`DeclarationExtractor` is stateless and dependency-free; `extract` is a pure function of
its input — the same OCR regions always produce the same `ExtractionResult`. Regions with
empty/whitespace text are dropped; if nothing usable remains, the result is an empty
`fields` list plus a warning ("No usable OCR text was available…"), never a fabricated
field.

## 3. Confidence is layered, never merged

Three confidences are kept **separate**, exactly as the spec requires:

| Confidence            | Owner        | Meaning                                           |
| --------------------- | ------------ | ------------------------------------------------- |
| `ocr_confidence`      | OCR (Ph. 12) | How sure OCR was of the *characters*.             |
| `extraction_confidence` | Extraction | How sure *this layer* is of the field reading.    |
| (legal assessment)    | Engine (Ph.16) | Whether the value is legally compliant.         |

`extraction_confidence = clamp(ocr_confidence × pattern_weight)`, where the pattern
weight encodes how much a given match pattern is trusted (a keyword-anchored clean number
is `0.97`; a spatial-proximity fallback `0.85`; an OCR-confused reading `0.42–0.50`; an
ambiguous unit/year `0.45`). A missing OCR confidence defaults to `0.9` so a provider that
does not score regions still yields usable extraction confidences.

`DETECTED_CONFIDENCE_THRESHOLD = 0.6` is declared locally and mirrors the engine's
`UNCERTAIN_CONFIDENCE_MAX`; a test asserts the two stay consistent so extraction never
imports the compliance package yet never drifts from it.

## 4. Status: `DETECTED` vs `UNCERTAIN` — and never a fabricated absence

Each field's `DetectionStatus` is decided by `_decide_status`:

- **`UNCERTAIN`** when more than one *distinct* `(value, unit)` reading was found (the
  extractor never arbitrarily picks a winner), **or** when the best candidate's
  extraction confidence is below `0.6`.
- **`DETECTED`** only when there is a single confident reading.

Extraction emits **only `DETECTED` or `UNCERTAIN`**. It never emits `CONFIRMED_ABSENT` or
`NOT_DETECTED`: a field for which no candidate was found is simply **omitted** from
`ExtractionResult.fields`. "Not detected in this scan" is deliberately *not* the same as
"absent from the product" — that determination belongs to the engine, gated on
`label_readable` (see `docs/scan-pipeline.md` §2).

## 5. OCR digit confusion → preserved candidates, not silent rewrites

The canonical example from the spec, `"MRP ₹5O"` (letter O for zero), is handled without
guessing:

- `contains_digit_confusion("5O")` is true (a real digit mixed with an OCR-confusable
  character), so the field becomes **`UNCERTAIN`**.
- **Both** candidates are preserved: the as-read `"5O"` (`note="ocr_confusion:as_read"`,
  weight `0.42`) and the corrected `"50"` (`note="ocr_confusion:corrected"`, weight
  `0.50`). `raw_text` keeps the original OCR text on every candidate so a reviewer sees
  exactly what was read.
- A purely alphabetic token is **not** treated as a misread number (too ambiguous to
  guess from), so ordinary words never masquerade as values.

Two-digit years are treated the same way: the century is a genuine guess, so the raw token
is kept with `note="ambiguous_year"` and the field is `UNCERTAIN`, rather than being
silently normalised to a specific century.

## 6. Fields extracted

`run_extractors` runs a fixed, ordered registry (stable output across runs) and drops any
field with no candidates:

| Field               | Signals used                                                        |
| ------------------- | ------------------------------------------------------------------- |
| `commodity_name`    | Explicit `Name:` / `Product name:` label only (conservative).       |
| `net_quantity`      | `Net Qty/Weight/Vol` keyword; number+unit token; unit canonicalised to an engine-parseable subset (`g/kg/mg/ml/l/pcs`). |
| `mrp`               | `MRP` / `Maximum Retail Price` / `₹`/`Rs`/`INR` anchor; numeric token; `INR` unit when a currency mark is present. |
| `manufacturer`      | `Manufactured by` / `Marketed by`; falls back to `Packed by`/`packer`. |
| `manufacture_date`  | `MFG` / `Mfd` / `Date of manufacture` + numeric or month-name date. |
| `packing_date`      | `Packed` / `Packing` / `PKD` + date.                                |
| `import_date`       | `Date of import` / `Imported on` + date.                            |
| `consumer_care`     | `Consumer/Customer care` / `helpline` / `toll-free` + email/phone.  |
| `country_of_origin` | `Country of origin` / `Made in` / `Product of`.                     |

**Spatial proximity** is a *fallback only*: when a keyword's value sits in a separate OCR
region, `_near_regions` finds the region to the right on the same line, then below, using
bounding boxes. When boxes are unavailable it returns nothing, so extraction degrades to
single-region matching rather than guessing across the label.

**Unit discipline:** the canonical net-quantity units are a deliberate subset chosen so a
`DETECTED` net-quantity string is always re-parseable by the engine's own
`parse_quantity`; a dedicated test asserts this. A number with an unrecognised unit is
kept as a **low-confidence** candidate (`note="unrecognised_unit"`) so the engine routes
it to manual review rather than dropping it or raising a false finding.

## 7. Adapting DOWN to the engine contract

`FieldExtraction.to_extracted_declaration()` carries the **best** candidate's value/unit
and confidence but **keeps the status intact** — an `UNCERTAIN` field stays `UNCERTAIN`,
so the engine routes it to manual review instead of trusting a guessed value. This mirrors
the codebase's established rich-model → stable-contract pattern (`ImageQualityReport` →
`ImageQualityResult`, `RawTextRegion` → `OCRResult`). All candidates remain available on
the richer `ExtractionResult` for review/UI; only the adapter output crosses into the
engine.

## 8. What Phase 15 does not do

- No LLM, no NLP model, no external service or database lookup — deterministic only.
- No legal interpretation, no compliance status, no severity.
- No assertion that a declaration is absent (the engine decides that, conservatively).
- No change to `ComplianceEngine`, validators, resolver, DB models, migrations, or the
  `declarations` `CHECK` constraint. No new tables, no API endpoint.

## 9. Tests

`tests/extraction/` — **38 tests** covering normalisation, OCR-confusion candidate
preservation (`"5O"` → both candidates, `UNCERTAIN`), ambiguous-year handling,
proximity fallback, unit canonicalisation and the engine-parseable-unit invariant,
per-field extraction, and determinism. Suite after Phase 15: **330 passed, 2 skipped**
(was 292 + 2). No regressions.
