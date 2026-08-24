# Legal rule storage

Phase 6 stores versioned Legal Metrology rule metadata. It does not decide whether a product is compliant.

## Architecture

```text
legal-rules/2011/rules.json
        ↓
   seeds/legal_rules.py
        ↓
   LegalRuleRepository
        ↓
   PostgreSQL legal_rules
        ↓
   RuleLoader (read API for later engine phases)
```

The future engine will call `RuleLoader.select_for_inspection(context)` and run validators only on `APPLICABLE` rows. Unverified rows are listed separately and are never treated as production law.

## Table

`legal_rules` (created in Phase 4, extended in Phase 6):

| Column | Role |
| --- | --- |
| `rule_code` | Internal LabelGuard id, e.g. `LM-PC-MRP-001` |
| `source_reference` | Official clause, e.g. `Rule 6(1)(e)`, or null |
| `source_version` | `2011`, `2011-amended-YYYY`, … |
| `effective_from` / `effective_to` | Version window. Null `effective_to` means still open |
| `applicability_condition` | JSON: categories, exclusions, notes |
| `rule_status` | `DRAFT`, `ACTIVE`, `RETIRED` |
| `verification_status` | `VERIFIED`, `UNVERIFIED`, `NEEDS_REVIEW` |
| `is_prototype` | True for this MVP set |

Unique key: `(rule_code, source_version, effective_from)`.

## Versioning

An inspection on date D uses the row where `effective_from <= D` and (`effective_to` is null or `>= D`). A 2026 amendment does not change a 2023 inspection.

To add an amendment, call `LegalRuleRepository.update_rule_version`: it sets the previous `effective_to` to the day before and inserts a new row. Old rows are never deleted.

## Authoritative vs draft

`get_authoritative_rules()` returns only `ACTIVE` + `VERIFIED`. `LM-PC-ORIGIN-001` is `DRAFT` / `UNVERIFIED` and will not be treated as production law.

Severity is `UNSPECIFIED` unless a later project policy assigns one. The 2011 Rules do not publish HIGH/MEDIUM labels.

## Seed

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m seeds.legal_rules
```

Running it twice updates existing versions. It does not insert a second `LM-PC-MRP-001` / `2011` / `2011-04-01` row.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/compliance
```
