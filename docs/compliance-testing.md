# Compliance testing

Phase 10 hardens the Legal Metrology core **without OCR**.

Declarations are built by hand. That is intentional. The legal pipeline must be testable even when computer vision is wrong, slow, or missing.

```text
Manual Declaration fixtures
        ↓
RuleResolver (version + applicability)
        ↓
ValidatorRegistry
        ↓
ComplianceEngine
        ↓
ComplianceAssessment
```

## Why OCR uncertainty must not become a legal violation

OCR often fails on glare, blur, a cropped photo, or a wrinkled label.

`NOT_DETECTED` means “extraction did not read this field.”

It does **not** mean “the packager left the field off.”

If the engine treated every unread MRP as a violation, LabelGuard would accuse products because the camera failed. That is unsafe for an inspection tool that is **not** a legal authority.

| Evidence | Result |
| --- | --- |
| Field unread, confidence 0.40 | `MANUAL_REVIEW` |
| Label judged readable **and** extractor is confident the field is absent | may be `POTENTIAL_NON_COMPLIANCE` |
| Value detected and structurally invalid (`-50`, `abc g`) | `POTENTIAL_NON_COMPLIANCE` |

The caller must set `label_readable=True`. Validators never infer that from a low OCR score.

## Test layers

| Level | What | Where |
| --- | --- | --- |
| Unit | One validator or one selector | `test_validators.py`, `test_edge_cases.py`, `test_rule_selection.py` |
| Integration | Resolver + registry + engine | `test_engine.py`, `test_pipeline.py` |
| Domain end-to-end | Full fixture inspection | `test_pipeline.py` using seed + fixture rules |

Postgres is not required. Persistence tests stay skipped when the database is down.

Reusable data lives in `backend/tests/fixtures/`.

## Status aggregation

```text
POTENTIAL_NON_COMPLIANCE  >  MANUAL_REVIEW  >  COMPLIANT
```

`PASS` and `NOT_APPLICABLE` are not failures.

Zero applicable verified rules → `MANUAL_REVIEW`, never `COMPLIANT`.

`assessment_confidence` stays `null`. There is no average of OCR scores.

## Rule versions

Non-overlapping windows:

| Inspection | Version |
| --- | --- |
| 2024-06-01 | A (`2023-01-01` … `2024-12-31`) |
| 2026-06-01 | B (`2025-01-01` … open) |

A future window is not evaluated. An expired window is not current, but the same row still applies to a date inside its window.

**Overlap** (two open windows on the same date) is a data error. The resolver records `OVERLAP` and does **not** pick the later `effective_from`. The engine returns `MANUAL_REVIEW` with a clear warning.

## Applicability and unverified rules

Category filters come from stored `applicability_condition` only.

Example from the 2011 prototype set: packaged food excludes Rule 6(1)(a) and 6(1)(d).

`UNVERIFIED` / `DRAFT` rows never become violations. They are warnings plus `MANUAL_REVIEW`.

## Failures that must not look like success

| Situation | Status |
| --- | --- |
| No registered validator | `MANUAL_REVIEW` |
| Validator exception | `MANUAL_REVIEW` (stack in server logs only) |
| Overlapping versions | `MANUAL_REVIEW` |
| No applicable verified rules | `MANUAL_REVIEW` |

## Historical reproducibility

The same declarations plus the same stored versions must produce the same assessment. Adding a later version must not change an older inspection date.

## Language

Tests and explanations use “automated assessment”, “potential non-compliance”, “manual verification recommended”, and “insufficient evidence”. They do not say a product is legal or illegal.
