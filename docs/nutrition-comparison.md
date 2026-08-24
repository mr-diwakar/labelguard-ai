# Multi-product nutrition comparison

Phase 13. Lets a consumer compare several **already-scanned** products by the
nutrition parameters they care about, and get a **deterministic, explainable**
ranking.

It is decision support for a shopper. It is **not** a dietitian, a health
verdict, or a medical recommendation. The output says a product *"ranks highest
based on your selected parameters"* — never that it is "healthiest".

```text
ComparisonRequest  (products[], priorities[])
        ↓
build_normalized_table     units.py — everything to a canonical unit
        ↓
resolve_priorities         scoring.py — dedupe, fill default directions
        ↓
build_scoreboard           scoring.py — min-max sub-scores, weighted, ranked
        ↓
explanation.py             ✓/⚠ highlights, comparative headline
        ↓
ComparisonResult  (rankings, winner, criteria, explanation, warnings)
```

This feature performs **no OCR and no nutrition extraction**. It consumes data
that the existing app already produced (Teammate 2's `NutritionResult`).

## Where it lives

Isolated under `app/nutrition/comparison/`, beside `app/compliance/`. It does
not modify the Legal Metrology engine, OCR, extraction, verification, auth, the
database, or any shared router.

| File | Responsibility |
| --- | --- |
| `parameters.py` | Static vocabulary: the 10 supported parameters, canonical units, unit family, default direction, extractor aliases. No data, no scoring. |
| `units.py` | Deterministic unit normalisation to a canonical unit (`Decimal`-based). Missing → `NOT_DETECTED`, never 0. |
| `schema.py` | Pydantic request/response contracts (`APIModel`, `extra='forbid'`). |
| `scoring_normalization.py` | Builds the `{product: {parameter: NormalizedValue}}` table from raw input, collecting warnings. |
| `scoring.py` | The deterministic core: min-max sub-scores, per-product weight renormalisation, ranking, tie detection. |
| `explanation.py` | Comparative ✓/⚠ highlights and headline. Never a health claim. |
| `service.py` | Orchestration (`compare`) + adapters from `NutritionResult`. |

## Supported parameters

| Parameter | Canonical unit | Default direction |
| --- | --- | --- |
| `CALORIES` | kcal | lower is better |
| `SUGAR` | g | lower is better |
| `ADDED_SUGAR` | g | lower is better |
| `PROTEIN` | g | **higher** is better |
| `CARBOHYDRATES` | g | lower is better |
| `FAT` | g | lower is better |
| `SATURATED_FAT` | g | lower is better |
| `TRANS_FAT` | g | lower is better |
| `FIBER` | g | **higher** is better |
| `SODIUM` | mg | lower is better |

Default direction is a **comparison convenience** (used when the consumer picks
a parameter without saying which way is "better"), not dietary advice. Any
priority can override it with an explicit `direction`.

Extractor aliases are resolved (`total_sugars` → `SUGAR`, `energy_kcal` →
`CALORIES`, `na` → `SODIUM`, `saturates` → `SATURATED_FAT`, `fibre` → `FIBER`,
etc.). Unknown keys are ignored with a warning — never scored, never zeroed.

## Unit normalisation

Every value is converted to its parameter's canonical unit before comparison so
products are compared apples-to-apples.

- Mass family base unit: gram (`mcg`/`µg`/`ug`, `mg`, `g`/`gm`/`gram`, `kg`).
- Energy family base unit: kilocalorie. On labels "Calories" means kcal, so a
  bare `cal`/`calorie` is treated as `kcal`. Kilojoules convert at
  **1 kcal = 4.184 kJ**.
- A missing/blank unit means "already in the canonical unit" — the common case
  when an extractor emits a bare number.
- Values may be numbers, numeric strings, or strings that carry their own unit
  (`"1500 mg"`, `"1,200 kcal"`). An explicit `unit` argument wins over one
  embedded in the string.

`normalize()` returns a status, never a silent fallback:

| Status | Meaning | Scored? |
| --- | --- | --- |
| `OK` | Converted to canonical unit | Yes |
| `NOT_DETECTED` | Value absent/blank | No |
| `UNRECOGNIZED_UNIT` | Unit not in the family table | No (warned) |
| `INVALID_VALUE` | Negative, non-numeric, or boolean | No (warned) |

## Scoring formula

Deterministic and reproducible by hand. **No LLM, no randomness.**

**1. Per parameter — min-max sub-score in `[0, 1]`** over the *participants*
(products that actually have a usable value), where 1 is most preferred:

```text
LOWER_IS_BETTER :  sub = (max - v) / (max - min)
HIGHER_IS_BETTER:  sub = (v - min) / (max - min)
```

A parameter is **non-differentiating** (excluded from scoring, still reported)
when fewer than two products have it, or every value is equal (`max == min`).

**2. Per product — weighted average over the parameters it HAS**, with the
caller's weights rescaled to sum to 1 across differentiating parameters:

```text
score(X) = Σ_{p ∈ have(X)} w_p · sub(X, p)  /  Σ_{p ∈ have(X)} w_p      (×100)
```

The denominator is the weight of the parameters the product *actually has*. This
is the core fairness rule: a product is **never** penalised with an implicit 0
for a missing parameter, nor rewarded for one.

**3. Rank by score descending.** Standard competition ranking (equal score +
coverage share a rank). Ties are flagged. Input order breaks ordering ties so
output is stable.

`coverage` (0..1) reports the fraction of differentiating weight a product had
data for, so a high score built on thin coverage is **visible**, not hidden.

## Missing-data handling

Missing data is a first-class concept, never silently zero.

- A missing/blank value is `NOT_DETECTED`. It is excluded from that parameter's
  min-max, and the product is scored only on what it has.
- Every ranking lists `not_detected_parameters` — the selected priorities the
  product had no data for — and each table cell shows `NOT_DETECTED` (or
  `UNAVAILABLE` for a present-but-unreadable value, with a note).
- If the top-ranked product was missing some selected parameters, a warning
  says so explicitly.
- A product is never disqualified for missing data; it is compared on its
  available parameters, with the gap made visible.

## Result language

- Headline: `"{Product} ranks highest based on your selected parameters."`
- Per-product highlights are comparative only:
  - `✓ Lowest sugar`, `✓ Highest protein`
  - `⚠ Higher calories than Product A`
  - `⚠ Protein not detected`
  - `• Equal fiber across products`
- Ties: `"{A} and {B} are tied ... based on your selected parameters."`
- No "healthiest", no medical or dietary claims anywhere.

## Usage

```python
from app.nutrition.comparison import (
    compare, ComparisonRequest, ProductNutritionInput,
    ComparisonPriority, Parameter, Direction,
)

result = compare(ComparisonRequest(
    products=[
        ProductNutritionInput(product_id="A", display_name="Product A",
                              nutrients={"sugar": "10 g", "protein": 5}),
        ProductNutritionInput(product_id="B", display_name="Product B",
                              nutrients={"sugar": "1500 mg", "protein": 9}),
    ],
    priorities=[
        ComparisonPriority(parameter=Parameter.SUGAR),            # default: lower better
        ComparisonPriority(parameter=Parameter.PROTEIN, weight=2),  # higher better, weighted
    ],
))

result.winner              # "B"
result.explanation[0]      # "Product B ranks highest based on your selected parameters."
```

### Feeding already-extracted data

The adapters are the **only** place that knows the extraction payload shape:

```python
from app.nutrition.comparison import product_from_nutrition_result

product = product_from_nutrition_result("A", nutrition_result, display_name="Product A")
# Returns None when the NutritionResult is unavailable/empty.
```

## HTTP API

Wired into the prototype at:

```text
POST /api/v1/nutrition/compare
```

Handler: [`app/api/nutrition.py`](../backend/app/api/nutrition.py), registered in
`app/api/router.py`. Request body is a `ComparisonRequest`; response is a
`ComparisonResult`. A structurally invalid request (e.g. a duplicate
`product_id`) returns HTTP 400 (`INVALID_COMPARISON`); malformed JSON is
rejected as 422 by the schema.

Run it:

```bash
cd backend
pip install -r requirements.txt
python -m app.main   # serves on http://127.0.0.1:8000, Swagger UI at /docs
```

Example:

```bash
curl -s http://127.0.0.1:8000/api/v1/nutrition/compare \
  -H 'Content-Type: application/json' \
  -d '{
    "products": [
      {"product_id": "A", "display_name": "Product A", "nutrients": {"sugar": "10 g", "protein": 5}},
      {"product_id": "B", "display_name": "Product B", "nutrients": {"sugar": "1500 mg", "protein": 9}}
    ],
    "priorities": [
      {"parameter": "SUGAR"},
      {"parameter": "PROTEIN", "weight": 2}
    ]
  }'
```

## Integration requirements (remaining — these touch shared/forbidden areas)

The HTTP endpoint above is **done**. Still open, deliberately out of scope:

1. **Persistence.** The planned `comparison_sessions` / `comparison_items`
   tables were **not** created (out of scope, and PROJECT_CONTEXT forbids
   creating them here). If comparison history is wanted, persist the
   `ComparisonResult` behind the existing database layer.
2. **Payload shape.** The adapters assume a flat
   `{nutrient: value}` / `{nutrient: {value, unit}}` payload. If Teammate 2's
   `NutritionResult.payload` differs, only `product_from_payload` /
   `product_from_nutrition_result` change.
3. **Mobile UI.** Rendering rankings, criteria, and highlights is a UI task; the
   response schema (`ComparisonResult`) is ready to consume, camelCase-friendly
   via the existing model conventions.

## Tests

`backend/tests/nutrition/` — run from `backend/` with `pytest`.

- `test_units.py` — normalisation, unit conversion, missing-vs-zero, bad input.
- `test_scoring.py` — min-max, weights, non-differentiating params, ties,
  determinism.
- `test_comparison_service.py` — the 14 required scenarios (S1–S14) end to end.
- `test_adapter.py` — bridging `NutritionResult` into comparison inputs.
- `test_api.py` — the `POST /nutrition/compare` handler and its 400 mapping.
