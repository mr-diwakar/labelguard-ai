# LabelGuard AI — Scan Pipeline: Legal, Verification, Guidance & Orchestration (Phases 16–19)

**Status:** `[IMPLEMENTED]` — the integration layers above declaration extraction
(Phase 15) and the Legal Metrology engine (`app/compliance/`), with tests.
**Not in this phase:** any change to the engine, validators, resolver, rules, DB, or
migrations; any external lookup; any LLM; any new nutrition-comparison logic; any
government-submission or complaint-filing capability.

This document describes the `app/pipeline/` package, which orchestrates the earlier
phases and adapts **DOWN** to their stable contracts. These modules **coordinate**; they
never re-implement a legal rule, an extractor, a verdict vocabulary, or the nutrition
comparator.

```text
extraction ─▶ legal ─▶ verification ─▶ guidance ─┐
 (Ph.15)     (Ph.16)     (Ph.17)        (Ph.18)   ├─▶ run_scan ─▶ ScanResult
                              nutrition (carried) ─┘   (Ph.19)
```

The guiding invariant: **LabelGuard has exactly one verdict system, and it lives in
`app/compliance`.** Every layer here re-reads a verdict something else already produced;
none invents one.

---

## 1. Package layout

Public API (`app/pipeline/__init__.py`) grows one milestone at a time:

- `legal.py` — Phase 16: `assess_extraction`, `declarations_for_engine`.
- `verification.py` — Phase 17: `verify`, `verify_one`, `measured_value_from_text`.
- `guidance.py` — Phase 18: `build_guidance`.
- `orchestrator.py` — Phase 19: `run_scan`.

New contracts/enums are all **additive**:

- `app/schemas/contracts/guidance.py` — `ConsumerGuidance`, `GuidanceItem` (Phase 18).
- `app/schemas/contracts/scan.py` — `ScanStageStatus` + two additive `ScanResult` fields
  `guidance` and `stages` (Phase 19); every earlier `ScanResult` construction still valid.
- `app/core/enums.py` — `Severity`, `FindingKind` (Phase 18); `StageOutcome` (Phase 19).

---

## 2. Phase 16 — Legal integration (`legal.py`)

An **adapter**, not a second engine. It converts a Phase 15 `ExtractionResult` into the
engine's `Declaration` inputs, invokes the unchanged `ComplianceEngine.evaluate`, and
returns the engine's own `ComplianceAssessment`.

```python
from app.pipeline import assess_extraction

assessment = assess_extraction(
    engine, extraction,
    inspection_date=..., product_category=..., is_imported=False,
    size_is_relevant=None, label_readable=None,
)
```

`declarations_for_engine` uses the existing `ExtractedDeclaration.to_declaration` mapping
(`DETECTED → DETECTED`, `UNCERTAIN → LOW_CONFIDENCE`, …); `NOT_APPLICABLE` fields map to
`None` and are dropped, because per-rule applicability is the resolver's job, not the
extractor's.

**Distinctions preserved** (all enforced by the engine it delegates to, never overridden):

- OCR failure ≠ a declaration being absent.
- Low OCR/extraction confidence ≠ non-compliance — it is manual review.
- A field not detected in one scan ≠ proof of omission.
- "Potential non-compliance" / "manual review" are never "fraud" or a legal verdict.

**The `label_readable` lever** is the one control governing "not detected ≠ omission".
Extraction never asserts a reliable absence, so an undetected required field is simply
missing from the declaration list. The engine's `presence_outcome` treats a missing
required field as `POTENTIAL_NON_COMPLIANCE` **only when `label_readable is True`** — an
explicit, independent determination that the whole label was legibly captured; otherwise
it routes to `MANUAL_REVIEW`. This adapter therefore **defaults `label_readable` to `None`
(unknown)** and never infers it from per-field OCR confidence. A caller passes `True` only
when a readability determination (e.g. the Phase 12 image-quality stage) justifies it —
which is what lets a *genuine* omission surface without a single OCR miss being mistaken
for one.

**Tests:** `tests/pipeline/test_pipeline_legal.py` — 8 tests.

---

## 3. Phase 17 — Label-to-product verification (`verification.py`)

Compares a value **declared** on the label against a value **observed in the same
captured image**. The current image is the **only** evidence source — no external
database, marketplace, or web lookup exists anywhere in the code.

```python
from app.pipeline import verify, verify_one, measured_value_from_text

results = verify(verification_inputs)   # list[VerificationResult]
```

**Outcome vocabulary is the existing `VerificationOutcome`** — nothing here ever emits
"fraud", "counterfeit", or a legal verdict:

| Situation                                   | Outcome                        |
| ------------------------------------------- | ------------------------------ |
| Printed values match (units reconciled)     | `MATCH`                        |
| Printed values genuinely differ             | `POTENTIAL_MISMATCH`           |
| Units not comparable automatically          | `MANUAL_REVIEW`                |
| No observed value / image too low-confidence | `COULD_NOT_VERIFY`            |

**Image degradation must never manufacture a mismatch.** Rotation, scale, lighting, blur,
compression, and distance arrive as a low `observation_confidence`; below
`OBSERVATION_CONFIDENCE_MIN = 0.6` the result is `COULD_NOT_VERIFY`, never
`POTENTIAL_MISMATCH`. No numeric tolerance is invented (the contract forbids it); the
equality check uses only float-representation hygiene (`1e-9` relative), which is **not** a
measurement tolerance. Units are reconciled within a dimension (mass `g/kg/mg`, volume
`ml/l`); cross-dimension or one-sided units yield `MANUAL_REVIEW` rather than a guessed
conversion.

**Physical-quantity limitation.** A camera cannot measure the actual mass or volume of the
contents. For fields in `PHYSICAL_QUANTITY_FIELDS` (`net_quantity`) the comparison is
explicitly *declared-printed vs visible-printed only*, and every such result appends
`PHYSICAL_QUANTITY_NOTE` saying so and pointing to a calibrated measurement as the real
confirmation.

**Tests:** `tests/pipeline/test_pipeline_verification.py` — 11 tests.

---

## 4. Phase 18 — Consumer guidance (`guidance.py`)

A **presentation layer**. It re-reads verdicts the engine and the verification layer
already produced and explains them for a consumer. It computes no new verdict, invents no
severity, and never contradicts `assessment.status` (the status is *echoed*, never
recomputed).

```python
from app.pipeline import build_guidance

guidance = build_guidance(assessment, verification, evidence=evidence)  # ConsumerGuidance
```

`ConsumerGuidance` carries the five mandated narrative sections plus structured items:

- **WHAT WE FOUND** / **WHY IT MATTERS** / **WHAT IS UNCERTAIN** / **WHAT EVIDENCE TO
  KEEP** / **WHAT YOU CAN DO NEXT** — always populated coherently, including the all-clear
  `COMPLIANT` case.
- `items: list[GuidanceItem]`, each `{issue, finding_kind, severity, source_reference,
  detail, recommended_evidence, next_steps, limitations}`.

**Mapping (never upgrades or invents a verdict):**

- Engine `violations` → `GuidanceItem(POTENTIAL_NON_COMPLIANCE)`, carrying the engine's
  `severity`, `rule_code`, and `reason`; its limitation states plainly that this is *not a
  proven violation — only the Legal Metrology authority can make a legal determination.*
- Engine `manual_review` → `GuidanceItem(MANUAL_REVIEW)` ("unconfirmed, not a problem
  found").
- Verification `POTENTIAL_MISMATCH` / `COULD_NOT_VERIFY` / `MANUAL_REVIEW` → a
  `MANUAL_REVIEW` item that carries the result `note` (including the physical-quantity
  caveat) verbatim into `detail`/`limitations`. `MATCH` / `NOT_APPLICABLE` produce **no**
  item — there is nothing for the consumer to act on.

**Evidence** reuses the existing `EvidenceReference`. `what_evidence_to_keep` =
dedupe(supplied evidence + per-item recommended evidence + a baseline set: product photo,
proof of purchase, packaging). Engine `ValidationEvidence` snapshots are adapted through a
`_safe_bbox` guard because `EvidenceReference` requires an ordered `[x1,y1,x2,y2]` box that
upstream evidence does not guarantee.

**Consumer-owned actions only.** `next_steps` are suggestions; LabelGuard performs none of
them. The `DISCLAIMER` states that *LabelGuard has not contacted any seller or authority
and has not filed any complaint; any next step is yours to take.* By construction the
guidance never claims LabelGuard acted, and there is no government-submission code.

**Tests:** `tests/pipeline/test_pipeline_guidance.py` — 10 tests (incl. assertions that
forbidden words `fraud/counterfeit/illegal/…` never appear and that no "we filed / reported
to the authority" claim is ever produced).

---

## 5. Phase 19 — Scan orchestration (`orchestrator.py`)

Assembles one unified `ScanResult` from the pieces above. It is a **coordinator**: every
verdict comes from the layer that owns it.

```python
from app.pipeline import run_scan

scan = run_scan(
    scan_id="scan_1",
    ocr_results=..., engine=..., context=...,      # legal needs engine + context
    verification_inputs=..., nutrition=..., product=..., ingredients=..., evidence=...,
)  # -> ScanResult
```

Five isolated stages, each wrapped so a failure or missing input is recorded — never
fatal:

| Stage          | `COMPLETED` when…            | `SKIPPED` when…                          | `FAILED` when…            |
| -------------- | ---------------------------- | ---------------------------------------- | ------------------------- |
| `extraction`   | extractor ran (even 0 fields)| —                                        | extractor raised          |
| `legal`        | engine evaluated             | no extraction, or no engine, or no context | engine raised            |
| `verification` | cross-check ran              | no `verification_inputs`                 | verifier raised           |
| `guidance`     | guidance built               | no completed assessment                  | builder raised            |
| `nutrition`    | facts attached               | `nutrition is None` (missing ≠ zero)     | —                         |

Design rules, all enforced:

- **Partial results, never a crash.** A caller always gets a `ScanResult` back; coverage
  is surfaced in `ScanResult.stages` (a `ScanStageStatus` per stage) and `warnings`. Stage
  errors are truncated to a short, non-leaky `"<stage> stage error [ExcType]: …"` detail.
- **Failures are surfaced, not hidden.** A skipped/failed legal stage leaves
  `legal_assessment = None` — **never an implied `COMPLIANT`**.
- **Legal does not depend on nutrition.** Missing nutrition is `None` (never zero) and
  never blocks or changes the legal result; the `nutrition` stage detail says so.
- **Nutrition comparison is not rebuilt here.** A single scan carries its own
  `NutritionFacts`, carried through unchanged; ranking *multiple* products remains the
  separate Phase 13 feature (`app.nutrition.comparison`, its own endpoint). No comparison
  runs inside a single scan.

### 5.1 Endpoint decision (deliberate)

The milestone said to add `POST /api/v1/scan` **only if the architecture requires it, with
no duplicate endpoints.** It was **not** added. `run_scan` needs a live `ComplianceEngine`
(built from DB/seed rules — not JSON-serializable) and OCR produced from images; a genuine
endpoint would require the full image→OCR→DB-rule-loading→engine wiring, which is beyond
this milestone and would ship a half-wired placeholder. The **orchestration function
`run_scan` is the delivered substance**; wiring it to a route (loading rules, running OCR)
is a later integration step, recorded here so the decision is explicit rather than an
omission.

**Tests:** `tests/pipeline/test_pipeline_orchestrator.py` — 8 tests (full scan; legal runs
when nutrition missing; nutrition carried unchanged; missing engine → legal skipped, not
implied compliant; empty scan never crashes; simulated engine failure → `FAILED` +
warning, no raise; verification + physical-caveat flow-through; determinism).

---

## 6. Test summary

`tests/pipeline/` — **37 tests** (legal 8, verification 11, guidance 10, orchestrator 8),
added on top of the 38 extraction tests. Full suite after Phase 19: **367 passed, 2
skipped** (was 292 + 2 before Phase 15). No regressions at any milestone.

## 7. What the pipeline does not change

`ComplianceEngine`, validators, resolver, all rules, DB models, migrations, the
`declarations` `CHECK` constraint, and the Phase 13 nutrition comparator are all
untouched. No new tables, no migrations, no new production API endpoint. Every new
contract field is additive with a default, so existing constructions and tests are
unaffected.
