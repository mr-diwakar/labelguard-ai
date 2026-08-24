# Compliance engine

Phase 9 produces an **automated Legal Metrology assessment**.

It is decision support. It is not a court, a Legal Metrology officer, or a certificate of compliance.

```text
ComplianceRequest
        ↓
RuleResolver  (Phase 7 applicability + version windows)
        ↓
applicable / not_applicable / unverified / future / expired
        ↓
ValidatorRegistry  (Phase 8)
        ↓
ValidationResult[]
        ↓
aggregate
        ↓
ComplianceAssessment
```

The engine does not contain `if mrp_missing` checks. Those live in validators.

## Inputs

`ComplianceRequest`:

```json
{
  "inspection_date": "2026-08-23",
  "product_category": "HOUSEHOLD_PRODUCT",
  "is_imported": false,
  "declarations": {
    "mrp": {"value": "50", "confidence": 0.98, "status": "DETECTED"}
  }
}
```

Declarations are the Phase 5 `Declaration` objects. A field-keyed map is accepted and converted. Integer values such as `50` become `"50"`.

`ComplianceEngine.evaluate(...)` also accepts the four-argument form:

```python
engine.evaluate(inspection_date, product_category, product_context, declarations)
```

## Outputs

`ComplianceAssessment.status` is one of:

- `COMPLIANT`
- `POTENTIAL_NON_COMPLIANCE`
- `MANUAL_REVIEW`

Items are grouped into `passed`, `violations`, `manual_review`, and `not_applicable`. Every evaluated item is also in `results`.

Each item keeps `rule_id`, `rule_code`, `rule_name`, `source_reference`, `source_document`, `source_version`, `result`, `confidence`, `reason`, `recommended_action`, `severity`, and `evidence`.

`assessment_confidence` is always `null`. There is no “87% compliant” score.

The `explanation` uses phrases such as “Automated assessment” and “Manual verification recommended.”

## Rule resolution

The engine calls `RuleResolver.resolve(ProductContext)`.

Production code can wrap `RuleLoader.select_for_inspection`. Tests use `StaticRuleResolver` with in-memory `LegalRuleRecord` rows. The engine never imports SQLAlchemy.

Phase 7 already chooses the in-force version (`effective_from` / `effective_to`) and buckets:

| Bucket | Engine action |
| --- | --- |
| `applicable` | Run the registered validator |
| `not_applicable` | Record `NOT_APPLICABLE` (not a failure) |
| `unverified` | `MANUAL_REVIEW` + warning. Never a violation |
| `future` / `expired` | Do not evaluate. Warning only |
| `overlaps` | `MANUAL_REVIEW` + warning. No silent version pick |

A 2023 inspection keeps version A even if version B exists for 2025.

## Validators

```text
rule.validation_type  →  registry.get(...)  →  validator.validate(...)
```

No validator for that type → `MANUAL_REVIEW` (“No validator is currently implemented for this applicable requirement.”).

A validator exception → `MANUAL_REVIEW` (“Validation could not be completed reliably.”). The stack stays in server logs.

## Aggregation

Priority:

```text
POTENTIAL_NON_COMPLIANCE  >  MANUAL_REVIEW  >  COMPLIANT
```

- Any `POTENTIAL_NON_COMPLIANCE` → overall `POTENTIAL_NON_COMPLIANCE`
- Else any `MANUAL_REVIEW` (including unverified rules or a missing validator) → `MANUAL_REVIEW`
- Else at least one `PASS` (with or without `NOT_APPLICABLE`) → `COMPLIANT`
- Zero applicable verified rules → `MANUAL_REVIEW` (“No verified applicable rules were available…”)

`NOT_APPLICABLE` and `PASS` are not failures.

`MANUAL_REVIEW` from low OCR confidence never becomes `POTENTIAL_NON_COMPLIANCE` in the engine.

## Example

Household soap, all required declarations detected:

```text
Rule 6(1)(a)–(e), 6(2) → PASS
Rule 6(1)(f) size     → NOT_APPLICABLE (size not relevant)
Origin draft          → not applicable to this category
```

Overall: `COMPLIANT`

Same pack, MRP `NOT_DETECTED` at confidence `0.40`:

Overall: `MANUAL_REVIEW` — insufficient evidence, not a recorded violation.

Same pack, MRP `-50` detected:

Overall: `POTENTIAL_NON_COMPLIANCE` — automated assessment only.

## Wiring

```python
from app.compliance.engine import ComplianceEngine
from app.compliance.resolver import StaticRuleResolver

engine = ComplianceEngine(StaticRuleResolver(rules))
assessment = engine.evaluate(request)
```

Later FastAPI and OCR layers will call this the same way. They must not live inside the engine.
