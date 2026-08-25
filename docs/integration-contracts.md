# LabelGuard AI — Integration Contracts & Shared Data Architecture (Phase 11)

**Status:** `[IMPLEMENTED]` — typed contracts, adapters, validation, and tests.
**Not in this phase:** OCR, the verification algorithm, the nutrition engine, ingredient
intelligence, evidence generation, PDF, mobile wiring, orchestration. Those remain
`[PLANNED]`.

This document describes the stable data interfaces that sit **around** the existing
Legal Metrology core so that future layers (extraction, verification, nutrition) can be
built and swapped without touching the deterministic rule engine.

---

## 1. Purpose and scope

Phase 11 answers one question: *what are the exact typed shapes that flow between a
scan and the legal engine, and back out to a caller?* It establishes those shapes as
Pydantic v2 models with validation and contract tests. It deliberately does **not**
implement the pipelines that will eventually produce or consume them.

The guiding invariant: **the Legal Metrology core is not rewritten, wrapped in an LLM,
or given new tolerances.** Contracts adapt *to* the engine; the engine is unchanged.

## 2. Architectural position

```text
   INPUT (scan)                 INTEGRATION CONTRACTS              EXISTING ENGINE            ASSESSMENT
 ┌──────────────┐   ExtractedDeclaration / InspectionContext   ┌───────────────────┐   ┌────────────────────┐
 │ image / OCR  │ ───────────────────────────────────────────▶ │ ComplianceEngine  │ ─▶│ ComplianceAssessment│
 │ user context │        (adapters map DOWN to Declaration)     │ Resolver+Validators│   │  (reused as-is)     │
 └──────────────┘                                               └───────────────────┘   └────────────────────┘
        │                                                                                          │
        │  ProductProfile / NutritionFacts / IngredientItem / VerificationResult / EvidenceReference
        └───────────────────────────────────────────────────────────────────────────────▶ ScanResult (aggregate)
```

Everything new lives under `backend/app/schemas/contracts/`. The engine, its validators,
and the `declarations` DB `CHECK` constraint keep using `DeclarationStatus` /
`ComplianceStatus` unchanged.

## 3. Layer map

| Contract | File | Reuses / relationship |
| --- | --- | --- |
| `ExtractedDeclaration`, `detection_to_declaration_status` | `contracts/detection.py` | Adapts DOWN to `schemas/declaration.py::Declaration` |
| `InspectionContext` | `contracts/context.py` | Builds `ProductContext` and `ComplianceRequest` |
| `EvidenceReference` | `contracts/evidence.py` | Complements existing `EvidenceItem` |
| `MeasuredValue`, `VerificationInput`, `VerificationResult` | `contracts/verification.py` | New; shape only |
| `NutritionValue`, `NutritionFacts` | `contracts/nutrition.py` | Complements `schemas/nutrition.py::NutritionResult` |
| `ProductProfile` | `contracts/product.py` | Pre-persistence peer of `ProductResponse` |
| `ScanResult` | `contracts/scan.py` | **Reuses** `assessment.py::ComplianceAssessment` |
| `IngredientItem` (extended) | `schemas/ingredient.py` | Additive optional fields |
| New enums | `core/enums.py` | Additive; documented mappings |

## 4. The status-vocabulary problem (why an adapter, not a new/extended enum)

The extraction layer needs to distinguish *"OCR failed to read this field"* from *"the
extractor is confident this field is absent from a readable label."* The engine's
`DeclarationStatus` (`DETECTED / NOT_DETECTED / LOW_CONFIDENCE / MANUALLY_VERIFIED`)
cannot express that, and it **cannot be extended**, because:

- `database/models/declaration.py` pins it with a `CHECK` constraint:
  `status IN ('DETECTED','NOT_DETECTED','LOW_CONFIDENCE','MANUALLY_VERIFIED')`; and
- the validators consume those exact values.

So Phase 11 adds a **separate extraction-layer enum**, `DetectionStatus`, plus an
adapter that maps it DOWN to `DeclarationStatus`. This follows the codebase's own
established pattern of layer-specific enums (e.g. `ValidationOutcome.PASS` is distinct
from `ComplianceStatus.COMPLIANT`). It is **not** a duplicate status system: there is
exactly one mapping, in one place, and it is tested exhaustively.

### Mapping (`detection_to_declaration_status`)

| `DetectionStatus` | → `DeclarationStatus` | Engine effect (with a required-field rule) |
| --- | --- | --- |
| `DETECTED` | `DETECTED` | value present → PASS |
| `UNCERTAIN` | `LOW_CONFIDENCE` | always uncertain → **MANUAL_REVIEW** |
| `NOT_DETECTED` | `NOT_DETECTED` | uncertain absence → MANUAL_REVIEW unless reliable |
| `CONFIRMED_ABSENT` | `NOT_DETECTED` **+ confidence ≥ 0.95** | reliable absence → **POTENTIAL_NON_COMPLIANCE** |
| `NOT_APPLICABLE` | `None` (dropped) | not fed to the engine as a declaration |

## 5. `ExtractedDeclaration`

One field the extraction layer produced. Fields: `field`, `value?`, `unit?`,
`confidence? (0..1)`, `status: DetectionStatus`, `source (=OCR)`, `source_reference?`,
`bbox? [x1,y1,x2,y2]`. `extra="forbid"` and an ordered-bbox validator reject malformed
input. `.to_declaration(label_readable=...)` returns the legal `Declaration` or `None`.

## 6. Adapter semantics (`ExtractedDeclaration.to_declaration`)

- `NOT_APPLICABLE` → `None` (applicability is decided per-rule by the resolver, not by
  feeding a not-applicable field to the engine).
- `CONFIRMED_ABSENT` → `Declaration(status=NOT_DETECTED, confidence=max(conf, 0.95))`.
  The engine's `validators/support.py::is_uncertain()` treats a `NOT_DETECTED` field as a
  *reliable absence* only when `label_readable is True` **and** `confidence >= 0.6`. The
  `0.95` constant guarantees the confidence half; the caller must also set
  `InspectionContext.label_readable = True`.
- `UNCERTAIN` → `LOW_CONFIDENCE` (the engine always treats this as uncertain).
- If a `CONFIRMED_ABSENT` field is adapted but the label is **not** marked readable, the
  engine safely falls back to `MANUAL_REVIEW` — **never** a silent `COMPLIANT`.

`CONFIRMED_ABSENT_CONFIDENCE = 0.95` is a local constant in `contracts/detection.py`; the
contract layer does not import engine internals (see §17).

## 7. `InspectionContext`

Wraps the engine's selection facts and adds scan metadata (`inspection_id`, `source`,
`product_identifier`, `rule_version_context`). Accepts `date` **or** `datetime` in
`inspection_datetime`, which drives historical rule selection (a 2024 inspection keeps
using 2024 rules — Phase 10 reproducibility). Two adapters:

- `.to_product_context()` → the facts the `RuleResolver` needs, nothing more.
- `.to_compliance_request(declarations)` → the existing `ComplianceRequest`.
  `ExtractedDeclaration` items are adapted (with `label_readable` threaded through) and
  `NOT_APPLICABLE` items dropped; legal `Declaration` items pass through unchanged.

## 8. `EvidenceReference`

A generic pointer to supporting evidence (`OCR_REGION`, `PRODUCT_IMAGE`, `MEASUREMENT`,
`USER_NOTE`, `DOCUMENT`, `OTHER`). It *references* evidence — it does not generate,
store, or process images, and creates no file-storage infrastructure. It complements the
existing `EvidenceItem` (which tracks generated-artefact status for the mobile overlay).
`bbox` is pixel `[x1,y1,x2,y2]`, consistent with `OCRResult`; the pixel→normalised
conversion for overlays is a later phase.

## 9. Verification contracts (shape only)

`MeasuredValue{value, unit?}`, `VerificationInput`, `VerificationResult`. The
**algorithm is not implemented.** Two principles are encoded structurally:

- **DECLARED vs OBSERVED are separate.** `expected` comes from the label; `observed`
  comes from a measurement or the user and always names its `ObservationSource`.
- **A missing observation is valid input** (`observed=None` → `COULD_NOT_VERIFY`).

`applicable_rule_code` links to a Legal Metrology rule only when one is genuinely
encoded; tolerances are not invented here.

## 10. `VerificationOutcome` vs `VerificationStatus`

`VerificationOutcome` (`MATCH / POTENTIAL_MISMATCH / COULD_NOT_VERIFY / MANUAL_REVIEW /
NOT_APPLICABLE`) is the result of a *label-to-product check*. It is a **different enum**
from the pre-existing `VerificationStatus` (`VERIFIED / UNVERIFIED / NEEDS_REVIEW`), which
records whether a legal *rule row* has been human-verified. The name collision is
deliberately avoided. **No status is ever `FRAUD` / `CHEATING` / `ILLEGAL`.**

## 11. `ObservationSource` (the camera cannot weigh)

`CALIBRATED_MEASUREMENT / USER_PROVIDED / EXTERNAL_EVIDENCE / VERIFIED_OBSERVATION /
OTHER`. A declared value is never an observation. A smartphone photo cannot measure mass,
so an observed quantity must arrive from an explicit, named source. This structurally
prevents the system from ever claiming the camera weighed a product.

## 12. Nutrition contracts (missing ≠ zero)

`NutritionValue{amount?, unit?, status?, source_reference?}` and `NutritionFacts` with
`energy, protein, carbohydrates, total_sugar, added_sugar, fat, saturated_fat, trans_fat,
fiber, sodium` plus `basis` / `serving_size`. The hard rule: **missing nutrition data is
never zero.** Two non-zero "unknown" shades are representable:

- a nutrient field left `None` → not extracted at all;
- `NutritionValue(amount=None)` → the line was seen but its number was unreadable.

A genuine declared `0 g` is `amount=0.0` with `status=DETECTED` (reusing `DetectionStatus`)
— the only way a zero appears. An empty `NutritionFacts()` carries no implied zeros.
Complements the teammate availability wrapper `NutritionResult`; does not replace it.

## 13. `ProductProfile` (pre-persistence)

The existing `ProductResponse` requires a database `UUID`. A scan in progress has no row,
so `ProductProfile` carries the same descriptive facts (`name, brand, category,
net_quantity, mrp, barcode, product_identifier`) with **every field optional and no
`id`**. `category` accepts an unknown string as well as `ProductCategory`, so an
unrecognised label category degrades to review rather than crashing validation.

## 14. `IngredientItem` extension (backward compatible)

`schemas/ingredient.py::IngredientItem` gained optional `normalized_name`, `position`,
`confidence`, `source_reference`. All default to absent, so existing
`{"name", "raw_text"}` payloads validate unchanged and no current consumer is affected.

## 15. `ScanResult` (the aggregate)

The shape a future orchestrator returns (**orchestrator not implemented**). It does not
restate the legal verdict — `legal_assessment` **reuses** the engine's own
`ComplianceAssessment`. Semantics of "nothing to report" never upgrade the legal status:

- `legal_assessment=None` → the engine has not run / could not run — **not** an implied
  `COMPLIANT`.
- `nutrition=None`, `ingredients=[]`, `verification=[]` → those layers had nothing to say.

## 16. Fail-safe guarantees (malformed never becomes COMPLIANT)

Verified by the real engine in `tests/contracts/test_integration_contracts.py`:

| Extraction input (required `mrp` rule, readable label) | Legal status |
| --- | --- |
| `CONFIRMED_ABSENT` | `POTENTIAL_NON_COMPLIANCE` |
| `UNCERTAIN` (conf 0.5) | `MANUAL_REVIEW` |
| `CONFIRMED_ABSENT`, label readability unknown | `MANUAL_REVIEW` (safe fallback) |
| `DETECTED` with empty value | `MANUAL_REVIEW` |
| `DETECTED` with `"50"` | `COMPLIANT` |

## 17. Dependency direction and how to extend

`contracts/detection.py` imports **schemas + `core.enums` only** — never the `compliance`
package. This one-way direction means a future OCR module can be replaced without
touching Legal Metrology logic, and the engine never learns about `DetectionStatus`.

To add a real layer later:
- **OCR/extraction** → produce `ExtractedDeclaration` + `InspectionContext`, call
  `to_compliance_request()`, hand the result to `ComplianceEngine.evaluate()`.
- **Verification** → consume `VerificationInput`, return `VerificationResult`. Never emit
  fraud verdicts; keep DECLARED and OBSERVED separate.
- **Nutrition** → populate `NutritionFacts`; leave unknowns `None`, never `0`.
- **Persistence** → map an accepted `ProductProfile` onto a `Product` row.

## 18. Testing

`tests/contracts/test_integration_contracts.py` (34 tests) covers: shape/validation and
`extra="forbid"`; exhaustive status mapping; adapter behaviour for every `DetectionStatus`;
context adapters; **integration through the real engine** for the truth table in §16;
verification shape + the no-fraud / observed-optional guarantees; nutrition
missing-≠-zero; product pre-persistence; ingredient backward compatibility; and the
`ScanResult` reuse of `ComplianceAssessment`. Full suite: **160 passed, 2 skipped**.

## 19. What Phase 11 deliberately did NOT do

No OCR/OpenCV/YOLO, no verification/nutrition/ingredient algorithms, no evidence/PDF
generation, no mobile integration, no auth, no cloud, no LLM, no barcode/QR, no product
comparison. No new DB tables and no schema redesign — contracts are persistence-independent.
No existing model, enum, validator, or migration was modified except the **additive**
enum and `IngredientItem` changes described above.
