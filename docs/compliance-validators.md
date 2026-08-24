# Compliance validators

Phase 8 checks **one Legal Metrology requirement at a time**.

It does not decide the overall inspection status. That is Phase 9.

```text
Declarations + one rule + context
        ↓
Validator
        ↓
ValidationResult  (PASS / POTENTIAL_NON_COMPLIANCE / MANUAL_REVIEW / NOT_APPLICABLE)
        ↓
future Compliance Engine
```

A validator answers:

> Does this particular requirement look satisfied from the evidence we have?

It does **not** answer:

> Is this package legally compliant?

## Architecture

Validators are plain Python classes.

They do not:

- talk to FastAPI
- query PostgreSQL
- run OCR
- read images
- call an LLM

The caller loads the rule (repository / loader) and the declarations (extraction or manual entry), then calls `validate(rule, declarations, context)`.

```text
Rule repository  →  LegalRuleRecord
Extraction       →  Declaration[]
Phase 7          →  applicable?  (optional on context)
                 ↓
            Validator
```

## ValidationResult

| Field | Meaning |
| --- | --- |
| `rule_id` | Stored UUID if present, otherwise `rule_code` |
| `rule_code` | LabelGuard identifier, e.g. `LM-PC-MRP-001` |
| `source_reference` | Official citation copied from the rule, e.g. `Rule 6(1)(e)`. Never invented. |
| `result` | One validator outcome |
| `confidence` | Confidence in **this assessment**, not OCR confidence |
| `reason` | Short human-readable explanation |
| `evidence` | Field, value, source, OCR confidence, bbox, status |
| `recommended_action` | Set for review / potential issues |
| `severity` | Copied from the stored rule. Validators do not pick severity. |

Outcomes:

| Result | Meaning |
| --- | --- |
| `PASS` | Enough evidence that the requirement appears satisfied |
| `POTENTIAL_NON_COMPLIANCE` | Enough evidence that the requirement appears not satisfied |
| `MANUAL_REVIEW` | Evidence is missing, blurry, low-confidence, or the rule is unverified |
| `NOT_APPLICABLE` | The rule does not apply to this product / context |

`PASS` is not the same as inspection status `COMPLIANT`. The future engine will combine many results.

## Uncertainty rule

`NOT_DETECTED` is **not** `MISSING`.

OCR often fails on glare, blur, or a cropped photo. Treating that as a legal violation would create false cases.

| Input | Result |
| --- | --- |
| `status=NOT_DETECTED`, `confidence=0.40` | `MANUAL_REVIEW` |
| `status=LOW_CONFIDENCE` | `MANUAL_REVIEW` |
| `status=NOT_DETECTED`, high confidence, **and** caller sets `label_readable=True` | may be `POTENTIAL_NON_COMPLIANCE` |

`label_readable=True` is a fact the caller must supply. Validators never infer it from a low OCR score.

## Confidence

OCR might say `0.98`. That is “how sure extraction is about the text.”

The validator may report `0.75` on a PASS. That is “how sure this check is about its own result.”

Those numbers are different on purpose. A clean parse is not a legal ruling.

`MANUALLY_VERIFIED` raises assessment confidence because a person confirmed the **text**. The value is still checked. A manually verified MRP of `-50` is still `POTENTIAL_NON_COMPLIANCE`.

## Validator registry

`backend/app/compliance/registry.py` maps `validation_type` → validator.

| `validation_type` | Validator |
| --- | --- |
| `REQUIRED_DECLARATION` | `RequiredDeclarationValidator` |
| `MRP_VALIDATION` | `MRPValidator` |
| `NET_QUANTITY_VALIDATION` | `NetQuantityValidator` |
| `DATE_VALIDATION` | `DateDeclarationValidator` |
| `CONSUMER_CARE_VALIDATION` | `ConsumerCareValidator` |

Unknown types (including `CONDITIONAL_REQUIREMENT` for Rule 6(1)(f)) return `None`. Phase 9 should send those to manual review, not invent a check.

The stored consumer-care row `LM-PC-CARE-001` is still `REQUIRED_DECLARATION` (Phase 6). `ConsumerCareValidator` is registered for a future mapping. Do not change seed law to fit the registry.

## Validators

### RequiredDeclarationValidator

Used for Rule 6(1)(a), 6(1)(b), and currently 6(2).

- Detected value → `PASS`
- Reliable absence → `POTENTIAL_NON_COMPLIANCE`
- Uncertain extraction → `MANUAL_REVIEW`
- Category excluded by the stored rule → `NOT_APPLICABLE`

### MRPValidator

Used for Rule 6(1)(e).

Checks that a retail-sale-price value exists and parses as a non-negative number. Currency prefixes such as `₹` are stripped. No extra formatting law is applied.

### NetQuantityValidator

Used for Rule 6(1)(c).

Accepts values such as `100 g` or `500 ml`, or `{"value": 100, "unit": "g"}`. The number must be positive and the unit must be a common weight, volume, or count token. This is structural parsing, not a full unit-law engine.

A bare number without a unit is `MANUAL_REVIEW`.

### DateDeclarationValidator

Used for Rule 6(1)(d).

Accepts `07/2026`, `2026-07`, and `2026-07-15`. Three-part dates are read as day/month/year. Impossible calendars (`2026-02-30`) and unparseable text are `POTENTIAL_NON_COMPLIANCE` only when the declaration itself is confident.

The validator does not decide *which* date (manufacture vs packing vs import) the package must show. That comes from the rule text.

### ConsumerCareValidator

Reusable check for consumer-complaint contact text.

It only asks: is something usable present, or is the value obvious noise (`???`)? It does **not** certify that a phone or e-mail format meets Rule 6(2).

## Unverified rules

If `rule_status` is not `ACTIVE` or `verification_status` is not `VERIFIED`, the validator returns `MANUAL_REVIEW`.

Country of origin (`LM-PC-ORIGIN-001`) stays a draft. Validators must not treat it as production law.

## Engine integration

Phase 9 (`docs/compliance-engine.md`) calls these validators through the registry. Do not invent an “87% compliant” score.
