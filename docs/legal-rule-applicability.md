# Rule versioning and applicability

Phase 7 answers one question:

> Which rule versions applied to this product on the inspection date?

It does not decide COMPLIANT / POTENTIAL_NON_COMPLIANCE / MANUAL_REVIEW.

## Inputs

```text
inspection_date
product category
is_imported
size_is_relevant (optional)
```

`RuleLoader.select_for_inspection(context)` loads stored rows and calls `evaluate_applicability`.

## Version selection

A version is in force when:

```text
effective_from <= inspection_date
AND (effective_to IS NULL OR inspection_date <= effective_to)
```

Datetimes are converted to a UTC calendar date before comparison. The selector does not use “the latest row in the table”.

Example:

| Version | Window |
| --- | --- |
| A | 2021-01-01 … 2024-12-31 |
| B | 2025-01-01 … open |

2023-06-01 → A. 2026-08-23 → B. Adding B later does not change a 2023 inspection.

If two versions are both in force on the same date (overlapping open windows), the resolver records `OVERLAP` and does not pick one.

## Decisions

| Decision | Meaning |
| --- | --- |
| `APPLICABLE` | In force, category matches, ACTIVE and VERIFIED |
| `NOT_APPLICABLE` | In force, but category or a recorded condition does not match |
| `EXPIRED` | No version covers the inspection date; all windows have ended |
| `FUTURE` | Inspection date is before the first version |
| `UNVERIFIED` | In scope, but not ACTIVE+VERIFIED — never treated as production law |
| `OVERLAP` | More than one version is in force; selection is refused |

The future engine should consume only `APPLICABLE` rows.

## Examples from the prototype set

- Packaged food + Rule 6(1)(a) manufacturer identity → `NOT_APPLICABLE` (Explanation III).
- Imported product + `LM-PC-ORIGIN-001` → `UNVERIFIED` (draft row; not in the 2011 India Code text).
- Rule 6(1)(f) dimensions → `APPLICABLE` only when `size_is_relevant` is true.
