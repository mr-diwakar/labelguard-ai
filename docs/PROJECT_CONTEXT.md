# LabelGuard AI — Master Project Context / Handoff Document

**Tagline:** Scan. Verify. Understand.

This is the **MASTER PROJECT CONTEXT** for LabelGuard AI.

Give this file to future AI coding assistants, teammates, developers, and integration agents. A future reader should understand the project **without previous chat history**.

---

## How to use this document

1. Read this file first.
2. Inspect the **actual master repository**.
3. Trust the code if this file and the code disagree.
4. Never treat planned work as implemented.
5. Never treat teammate work as integrated unless it is present in this master repository.

**Status labels used throughout (do not mix them):**

| Label | Meaning |
| --- | --- |
| `[IMPLEMENTED]` | Present and working in this master repository |
| `[PARTIALLY IMPLEMENTED]` | Schema, mock UI, or partial code exists; the feature is not complete |
| `[TEAMMATE WORK — NOT INTEGRATED]` | Contract, README mention, or external teammate work exists; **not** in master as a live module |
| `[PLANNED]` | Agreed next/near work. Not in source |
| `[FUTURE]` | Later ideas. Not next work. Not implemented |

---

## Recent changes (2026-08-25)

**Multi-product nutrition comparison (Phase 13) — a deterministic scoring engine exists locally, but is NOT yet committed to git.**

A deterministic, LLM-free comparison engine now exists in the working tree under `backend/app/comparison/` with full request/result Pydantic contracts and 75 passing unit tests. It is an in-process domain engine, tested with fixtures, in the same style as the legal `ComplianceEngine`. It is **not exposed over HTTP** and **not persisted to the database**. See **§15.1** for the complete subsystem description and the exact scoring formula.

> ⚠️ **Git state (verified 2026-08-25):** this work is **uncommitted local working-tree state — on no commit and no branch yet.** `git status` shows `app/comparison/`, `app/schemas/comparison.py` and `tests/comparison/` as **untracked (`??`)**, and `app/core/enums.py` + `app/schemas/__init__.py` as **modified-but-unstaged (` M`)**. The checkout sits on branch `feature/verification-modules`, but that branch currently **equals `main`** (`git rev-list --left-right --count main...feature/verification-modules` → `0  0`), so nothing has "landed on" it. Until it is committed the work is invisible to CI, clones and teammates, and would be lost by `git stash`, `git checkout .`, or a fresh checkout. **First durable step for whoever continues: commit these paths** (the owner did not authorise a commit in this session).

New status label used only for this work:

| Label | Meaning |
| --- | --- |
| `[IMPLEMENTED — uncommitted]` | Present, working and tested in the local working tree; **on no commit/branch** (untracked + unstaged files), no HTTP/DB wiring. Must be committed to be shareable. |

Everything else in this document describes committed code on `main`. Trust the code (and `git status`) over this file if they disagree.

---

# 1. Project identity

| Item | Value |
| --- | --- |
| Name | **LabelGuard AI** |
| Tagline | Scan. Verify. Understand. |
| Hackathon | Smart India Hackathon **2026** |
| Problem statement ID | **26034** |
| Problem | Software system to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels |
| Organization | Ministry of Consumer Affairs, Food & Public Distribution |
| Department | Department of Consumer Affairs |
| Primary domains | Legal Metrology; consumer protection; product label intelligence; computer vision; OCR; nutrition intelligence |

Official legal sources (do not invent requirements from unofficial sites):

- https://consumeraffairs.gov.in/pages/legal-metrology-act
- DoCA consolidated publication of the Legal Metrology (Packaged Commodities) Rules, 2011 with amendments
- India Code text of the 2011 Rules (G.S.R. 202(E), 7 March 2011) — used for the verified prototype seed

LabelGuard is a **decision-support and information platform**. It is **not** a legal authority, a court, a government complaints portal, a certificate of compliance, a calorie tracker, a food scanner, or an AI chatbot.

---

# 2. Current product direction

The product direction has evolved.

LabelGuard AI is primarily a:

**CONSUMER-FIRST AI-ASSISTED PRODUCT LABEL INTELLIGENCE AND LEGAL METROLOGY VERIFICATION PLATFORM.**

**Consumers are the PRIMARY audience.**

Do **not** position the current application primarily as an inspector-only application. Professional/enforcement functionality may remain possible in the architecture (same legal engine, same rules). It is **not** the primary current user experience.

The product should help consumers:

- scan products
- understand labels
- identify required declarations
- check applicable Legal Metrology requirements
- verify label claims against **current** observable evidence
- identify potential discrepancies
- understand nutrition
- compare multiple products
- preserve evidence
- generate useful reports
- make informed decisions

**Leftovers in master that do not match this identity (do not treat as product intent):**

- FastAPI description in `backend/app/main.py`: “AI-assisted Legal Metrology compliance inspection platform.”
- `users.role` default: `INSPECTOR`
- Mobile Home still shows mock inspection stats and “recent inspections”

---

# 3. Core USP

The primary USP is **not** generic food scanning, calorie tracking, an AI chatbot, or generic OCR.

The primary USP is:

**AI-ASSISTED LEGAL METROLOGY + LABEL-TO-PRODUCT VERIFICATION.**

Nutrition and ingredient intelligence are **secondary but important**.

Intended product loop:

```text
SCAN → READ → EXTRACT → VALIDATE → VERIFY → EXPLAIN → EVIDENCE → REPORT
```

Legal Metrology remains the primary **compliance** USP. Label-to-product verification is the **next major product feature**. An LLM must **never** be the final legal authority.

```text
OCR / AI
  ↓
Structured information
  ↓
Deterministic rule engine
  ↓
Compliance assessment
```

---

# 4. Two phase numbering systems (do not confuse them)

This repository uses **backend foundation phase numbers** in `backend/README.md` and test docstrings. The product owner has also defined a **product capability** phase list and a **new Phase 11+** roadmap.

A future AI **must** keep these distinct.

## 4.1 Backend foundation phases (what master actually completed)

These are the numbered phases **in this master repository**. Current backend README: **“Phase 10 — Testing and hardening.”**

| Backend phase | What it is | Master status |
| --- | --- | --- |
| 1 | FastAPI app + `/health` | `[IMPLEMENTED]` |
| 2 | Error envelope + request logging | `[IMPLEMENTED]` |
| 3 | Lazy PostgreSQL engine / session | `[IMPLEMENTED]` |
| 4 | SQLAlchemy models + Alembic tables | `[IMPLEMENTED]` |
| 5 | Pydantic contracts (`app/schemas/`) | `[IMPLEMENTED]` |
| 6 | Legal rule storage + seed from JSON | `[IMPLEMENTED]` |
| 7 | Rule versioning + applicability | `[IMPLEMENTED]` |
| 8 | Deterministic validators + registry | `[IMPLEMENTED]` |
| 9 | `ComplianceEngine` → `ComplianceAssessment` | `[IMPLEMENTED]` |
| 10 | Hardening, overlap detection, pipeline tests | `[IMPLEMENTED]` |

This is the **completed foundation**. It is **not** a complete consumer product. There is still no camera, OCR engine, scan API, verification engine, or nutrition engine.

## 4.2 Product capability phases (owner list — verified against master)

The owner’s expected product list is below. **Each row is verified against this master repository. Do not blindly mark COMPLETED.**

| Product phase | Name | Master status | What actually exists |
| --- | --- | --- | --- |
| 1 | Environment / project foundation | `[IMPLEMENTED]` | `backend/`, `mobile/`, `legal-rules/`, `docs/`, git, venv pattern, Expo 54 |
| 2 | FastAPI backend foundation | `[IMPLEMENTED]` | Health routes, logging, error envelope. **Not** a full product API |
| 3 | PostgreSQL / database | `[IMPLEMENTED]` (schema only) | 11 tables, Alembic head `0003_legal_rule_traceability`. No CRUD API |
| 4 | Legal Metrology rule engine | `[IMPLEMENTED]` (in-process) | `app/compliance/`. **Not** exposed as HTTP |
| 5 | Image processing | `[PLANNED]` | No OpenCV. Not in `requirements.txt` |
| 6 | OCR | `[PLANNED]` + `[TEAMMATE WORK — NOT INTEGRATED]` | `OCRResult` contract only. No PaddleOCR. Not installed |
| 7 | Declaration extraction | `[PLANNED]` | `Declaration` schema + `declarations` table. No extractor |
| 8 | OCR → extraction → compliance integration | `[PLANNED]` | Engine exists; **no** scan orchestrator, no OCR wiring. `ScanResponse` is unused schema |
| 9 | Evidence | `[PARTIALLY IMPLEMENTED]` + `[TEAMMATE WORK — NOT INTEGRATED]` | Table + schema + validator bbox + mock Evidence screen. No image generator, no EvidenceService |
| 10 | Nutrition | `[PLANNED]` + `[TEAMMATE WORK — NOT INTEGRATED]` | `NutritionResult` contract + `nutrition_data` table + Coming Soon tile. No nutrition engine |

**Phase 11 and later are `[PLANNED]` / `[FUTURE]` unless master proves otherwise. Master does not prove otherwise.**

---

# 5. What is in the master repository today

Root layout:

```text
labelguard/
├── backend/          FastAPI, schemas, DB, compliance engine, tests
├── mobile/           Expo 54 mock consumer UI
├── legal-rules/      Prototype 2011 rules JSON
├── docs/             This file + legal-engine docs
└── README.md
```

There is **no** `backend/app/verification/` package. There is **no** `app/ai/`, OpenCV, PaddleOCR, ReportLab, or Ollama. There is **no** teammate OCR/nutrition/CV implementation in this tree.

Live HTTP: **only** `GET /health` and `GET /api/v1/health`.

---

# 6. Implementation status (feature map)

| Feature | Status |
| --- | --- |
| FastAPI process | `[IMPLEMENTED]` |
| `GET /health`, `GET /api/v1/health` | `[IMPLEMENTED]` — `{"status":"ok"}` |
| Error envelope `{error:{code,message,details}}` | `[IMPLEMENTED]` |
| Request logging + secret redaction | `[IMPLEMENTED]` |
| Config via `.env` | `[IMPLEMENTED]` |
| PostgreSQL schema (11 tables) | `[IMPLEMENTED]` |
| Alembic `0001`–`0003` | `[IMPLEMENTED]` |
| Legal rules JSON + DB seed | `[IMPLEMENTED]` |
| Rule versioning + applicability | `[IMPLEMENTED]` |
| Deterministic validators + `ComplianceEngine` | `[IMPLEMENTED]` |
| Expo mock UI + 7 UI locales | `[IMPLEMENTED]` |
| Pydantic teammate contracts (OCR, nutrition, evidence, scan) | `[IMPLEMENTED]` (contracts only) |
| Evidence table + mock Evidence screen | `[PARTIALLY IMPLEMENTED]` |
| Inspection history table + mock History screen | `[PARTIALLY IMPLEMENTED]` |
| Camera / `expo-camera` | `[PLANNED]` |
| OpenCV image pipeline | `[PLANNED]` |
| PaddleOCR | `[PLANNED]` / `[TEAMMATE WORK — NOT INTEGRATED]` |
| Declaration extraction from images | `[PLANNED]` |
| Scan HTTP API | `[PLANNED]` |
| Label-to-product verification engine | `[PLANNED]` — **next major phase** |
| Nutrition engine | `[PLANNED]` / `[TEAMMATE WORK — NOT INTEGRATED]` |
| Multi-product nutrition comparison | `[IMPLEMENTED — uncommitted]` — deterministic scoring/ranking/explanation engine in `app/comparison/`, 75 tests. **Uncommitted working tree** (untracked/modified, on no commit), no API/DB. See §15.1 |
| Ingredient intelligence engine | `[PLANNED]` / `[TEAMMATE WORK — NOT INTEGRATED]` |
| Evidence image generation / PDF | `[PLANNED]` / `[TEAMMATE WORK — NOT INTEGRATED]` |
| Auth / passwords | `[PLANNED]` — not present |
| Historical current-vs-old-product comparison | **Not the product direction** — do not build as the core feature |
| Barcode, QR, offline, e-commerce, local LLM | `[FUTURE]` |

---

# 7. Label-to-product verification

**Status: `[PLANNED]` — next major feature (Phase 11).**

This is **not** historical product comparison. Do **not** design the primary system as:

```text
Current product  vs  old product version
```

Instead:

```text
THE LABEL PROVIDES THE EXPECTED CLAIM.
THE CURRENT PRODUCT / CURRENT OBSERVATION PROVIDES THE OBSERVED VALUE.
```

```text
                CURRENT PRODUCT
                     |
          +----------+----------+
          |                     |
          v                     v
      LABEL/TEXT          CURRENT OBSERVATION
          |                     |
          v                     v
         OCR              COMPUTER VISION /
          |                USER MEASUREMENT
          v                     |
    EXPECTED VALUE              |
          |                     |
          +----------+----------+
                     |
                     v
             VERIFICATION ENGINE
                     |
          +----------+----------+
          |          |          |
          v          v          v
        MATCH    POTENTIAL    COULD NOT
                 MISMATCH      VERIFY
```

## Example

Label: Net Quantity **500 g**. User scale: **472 g**.

```text
Declared:   500 g
Observed:   472 g
Difference:  28 g
```

Do **not** automatically say “Fraud”, “Cheating”, or “Illegal product.”

Say: **“Potential quantity discrepancy detected.”** Then apply applicable Legal Metrology requirements/tolerances **only if encoded from official sources**.

Possible states: `MATCH` | `POTENTIAL_MISMATCH` | `MANUAL_REVIEW` | `COULD_NOT_VERIFY` | `NOT_APPLICABLE`.

These verification states are **not** in `app/core/enums.py` today. Do not treat them as live API values.

**Name collision:** `VerificationStatus` already exists. It means whether a **legal rule row** is `VERIFIED` / `UNVERIFIED` / `NEEDS_REVIEW`. It is **not** a label-to-product result. Do not reuse it for MATCH/MISMATCH.

## Physical measurement rule

A normal smartphone camera **cannot** reliably determine physical mass. Never claim the camera measures grams.

```text
LABEL → OCR → Declared quantity
+
USER / EXTERNAL MEASUREMENT → Observed quantity
→
Declared vs Observed → Applicable rule / tolerance → Result
```

Physical millimetre measurement from an ordinary photograph requires calibration or a known reference. Never provide false precision. Pixels ≠ millimetres ≠ grams.

## Planned verification types

1. Quantity — 500 g vs 472 g  
2. Count — 10 pieces vs 9 pieces  
3. Text/value — MRP ₹50 vs visible MRP ₹50  
4. Product identity — named product vs current package  
5. Other observable consistency checks  

Preserve where applicable: expected value, observed value, difference, verification method, confidence, evidence, status, applicable rule.

## Planned module layout (files do **not** exist)

```text
backend/app/verification/     # PLANNED
  verifier.py
  quantity.py
  count.py
  text_match.py
  product_identity.py
  result.py
```

Do not create this package unless an implementation task asks for it. Keep it **beside** `compliance/`. Do not fold claim-vs-observation into random validator `if` statements.

---

# 8. Result language (mandatory)

Always distinguish:

| Concept | Meaning |
| --- | --- |
| `MATCH` | Observation agrees with the claim `[PLANNED]` |
| `POTENTIAL_MISMATCH` | Observation differs from the claim `[PLANNED]` |
| `COULD_NOT_VERIFY` | Insufficient evidence `[PLANNED]` |
| `MANUAL_REVIEW` | Human check recommended (also an **implemented** legal status) |
| `NOT_APPLICABLE` | Check does not apply |
| `COMPLIANT` | Implemented legal overall status — **not** a legal certificate |
| `POTENTIAL_NON_COMPLIANCE` | Implemented legal overall status |

Do **not** reduce every uncertainty to a violation.

If OCR cannot reliably read something, do **not** say “Information is missing.” Say **“Information could not be reliably verified.”**

Implemented engine wording already uses: “Automated assessment”, “potential non-compliance detected”, “manual verification recommended”, “insufficient evidence”, “this is not a legal determination.”

Consumer-facing legal language may use: Compliant, Potential Non-Compliance, Manual Review, Potential Mismatch, Could Not Verify — without pretending AI makes a final legal determination.

---

# 9. Target architecture vs current architecture

## Target (not all boxes exist)

```text
                 MOBILE APP
            React Native + Expo
                      |
                      v
                FASTAPI BACKEND
                      |
       +--------------+--------------+
       |              |              |
       v              v              v
    OpenCV        PaddleOCR       PostgreSQL
    [PLANNED]     [PLANNED]      [IMPLEMENTED schema]
       |              |
       +-------+------+
               |
               v
       INFORMATION EXTRACTION [PLANNED]
               |
       +-------+--------+
       |                |
       v                v
LEGAL METROLOGY     NUTRITION ENGINE
    ENGINE             [PLANNED]
 [IMPLEMENTED]
       |                |
       +-------+--------+
               |
               v
      LABEL-TO-PRODUCT VERIFICATION [PLANNED]
               |
               v
        RESULT ENGINE
               |
       +-------+--------+
       |       |        |
       v       v        v
    Legal  Verification Evidence
               |
               v
            Reports
```

## Current (master)

```text
MOBILE (Expo mock data)  ✗ not wired to API

FASTAPI
  GET /health
  GET /api/v1/health
        |
        +-- PostgreSQL schema (no CRUD API)
        +-- LEGAL METROLOGY CORE (in-process, fixture-tested)
```

---

# 10. Backend (current)

Root: `backend/`.

```text
backend/
  app/
    main.py                 FastAPI factory
    api/                    health + versioned router only
    core/                   config, enums, errors, logging
    database/               SQLAlchemy models, lazy engine
    schemas/                Pydantic contracts
    compliance/             legal core (no FastAPI/OCR/SQLAlchemy inside validators)
    comparison/             nutrition comparison engine (uncommitted/untracked; no FastAPI/DB inside)
  migrations/
  seeds/
  tests/
  requirements.txt
  alembic.ini
  pytest.ini
  .env.example
```

Python: **3.13+** required (3.14 has been used in this workspace). Venv: `backend/.venv`.

Dependency direction (keep this):

```text
API → (future services) → ComplianceEngine → RuleResolver → ValidatorRegistry → Validators
```

`RuleLoader.resolve()` wraps `select_for_inspection()`. Tests use `StaticRuleResolver`.

`get_db()` exists but is unused by routes. The API **starts without** Postgres. Persistence tests **skip** if Postgres is down.

Installed packages: FastAPI, Uvicorn, Pydantic, pydantic-settings, SQLAlchemy, Alembic, psycopg, pytest, pytest-cov, httpx.

**Not** installed: OpenCV, PaddleOCR, ReportLab, Ollama.

---

# 11. Legal Metrology engine `[IMPLEMENTED]`

In-process domain service. **Not HTTP. Not an LLM.**

```text
ComplianceRequest
  inspection_date, product_category, is_imported, size_is_relevant,
  label_readable, declarations
        ↓
RuleResolver.resolve(ProductContext)
        ↓
applicable / not_applicable / unverified / future / expired / overlaps
        ↓
ValidatorRegistry.get(validation_type)
        ↓
ValidationResult → aggregate → ComplianceAssessment
```

`ComplianceStatus`: `COMPLIANT` | `POTENTIAL_NON_COMPLIANCE` | `MANUAL_REVIEW`.

`ValidationOutcome`: `PASS` | `POTENTIAL_NON_COMPLIANCE` | `MANUAL_REVIEW` | `NOT_APPLICABLE`.

`PASS` is **not** inspection `COMPLIANT`.

Aggregation: `POTENTIAL_NON_COMPLIANCE` > `MANUAL_REVIEW` > `COMPLIANT`.

Zero applicable verified rules → `MANUAL_REVIEW`. Missing validator, validator exception, overlapping versions, unverified/draft rules → `MANUAL_REVIEW`, not a violation. Unverified rules cannot become violations.

`ComplianceAssessment.assessment_confidence` is always `null`. Do not invent an overall “87% compliant” score. Per-check validator confidence exists in `validators/support.py`.

| `validation_type` | Validator | Notes |
| --- | --- | --- |
| `REQUIRED_DECLARATION` | `RequiredDeclarationValidator` | `[IMPLEMENTED]` |
| `MRP_VALIDATION` | `MRPValidator` | `[IMPLEMENTED]` |
| `NET_QUANTITY_VALIDATION` | `NetQuantityValidator` | `[IMPLEMENTED]` |
| `DATE_VALIDATION` | `DateDeclarationValidator` | `[IMPLEMENTED]` |
| `CONSUMER_CARE_VALIDATION` | `ConsumerCareValidator` | `[IMPLEMENTED]`; seed CARE row is still `REQUIRED_DECLARATION` |
| `CONDITIONAL_REQUIREMENT` | none | Size rule → `MANUAL_REVIEW` if applicable |
| `TEXT_FORMAT` / `READABILITY` | none | Enum only |

### Seed rules (`legal-rules/2011/rules.json`)

Rules live **outside** random Python files. Seed via `python -m seeds.legal_rules`.

| Code | Source | Type | Status |
| --- | --- | --- | --- |
| `LM-PC-MFR-001` | Rule 6(1)(a) | REQUIRED_DECLARATION | VERIFIED; excludes packaged food |
| `LM-PC-NAME-001` | Rule 6(1)(b) | REQUIRED_DECLARATION | VERIFIED |
| `LM-PC-NETQ-001` | Rule 6(1)(c) | NET_QUANTITY_VALIDATION | VERIFIED |
| `LM-PC-DATE-001` | Rule 6(1)(d) | DATE_VALIDATION | VERIFIED; excludes food and cosmetic |
| `LM-PC-MRP-001` | Rule 6(1)(e) | MRP_VALIDATION | VERIFIED |
| `LM-PC-SIZE-001` | Rule 6(1)(f) | CONDITIONAL_REQUIREMENT | VERIFIED; only when `size_is_relevant` |
| `LM-PC-CARE-001` | Rule 6(2) | REQUIRED_DECLARATION | VERIFIED |
| `LM-PC-ORIGIN-001` | not in the 2011 India Code text used | REQUIRED_DECLARATION | DRAFT / UNVERIFIED |

Internal `rule_code` values are LabelGuard IDs, not government numbers. Seed severity is `UNSPECIFIED`. Rows are `is_prototype: true`.

Rule records support: rule code, name, description, category, requirement, validation type, severity, source document, source version, effective date, expiry date, applicability condition. **Versioning is `[IMPLEMENTED]`.**

In force when:

```text
effective_from <= inspection_date
AND (effective_to IS NULL OR inspection_date <= effective_to)
```

Aware datetimes become a UTC calendar date. Do **not** silently pick the latest row. Overlap → `ApplicabilityDecision.OVERLAP` → `MANUAL_REVIEW`. Unique DB key: `(rule_code, source_version, effective_from)`. Never delete historical rows to “update” a rule.

Deeper docs: `docs/legal-rule-storage.md`, `docs/legal-rule-applicability.md`, `docs/compliance-validators.md`, `docs/compliance-engine.md`, `docs/compliance-testing.md`.

Applicable declarations (manufacturer, packer, importer, address, origin, generic name, net quantity, MRP, dates, consumer care, unit sale price, dimensions, others) are controlled by **this engine**, not by an LLM. Extraction of those fields from images is still `[PLANNED]`.

---

# 12. Information extraction `[PLANNED]` as a pipeline

`Declaration` contract and `declarations` table: `field`, `value`, `confidence`, `source` (`OCR` / `MANUAL` / `SYSTEM`), optional pixel `bbox`, `status`.

Statuses: `DETECTED` | `NOT_DETECTED` | `LOW_CONFIDENCE` | `MANUALLY_VERIFIED`. There is **no** `MISSING` status.

`NOT_DETECTED` means extraction found nothing. It is **not** automatically legally missing. `NOT_DETECTED` + low OCR confidence → `MANUAL_REVIEW`.

Validator field aliases (`validators/support.py`) include manufacturer/packer/importer, `commodity_name`/`name`, `net_quantity`, date fields, `mrp`/`retail_sale_price`, consumer care, `country_of_origin`. There is no extractor from OCR text.

Preserve: value, confidence, bounding box, source, extraction method.

---

# 13. OCR and image processing

**OCR engine:** `[PLANNED]` / `[TEAMMATE WORK — NOT INTEGRATED]`.

Planned engine: PaddleOCR. Not installed. No CPU/GPU init, language list, or preprocessing code in master.

Contract (`app/schemas/ocr.py`):

- `OCRResult`: `text`, `confidence` in `[0, 1]`, `bbox: [x1, y1, x2, y2]` pixels (`x2 >= x1`, `y2 >= y1`)
- `ImageQualityResult`: `usable`, optional `reason`

OCR/AI may do: image understanding, text detection, OCR, extraction, classification, normalization, explanation. They must **not** make final legal decisions.

Intended image pipeline `[PLANNED]`:

```text
Image → Quality check → Blur → Brightness/glare → Rotation → Perspective
  → Enhancement → OCR
```

Poor-quality images should yield: **“Image quality insufficient. Please capture the label again.”** — not unreliable compliance conclusions.

Mobile evidence overlay uses normalised `x, y, width, height` in `[0, 1]`. Pixel OCR boxes need a future adapter. That conversion is **not implemented**.

---

# 14. Evidence `[PARTIALLY IMPLEMENTED]`

Current: table `evidence` (`AVAILABLE` / `UNAVAILABLE` / `FAILED`); schemas `EvidenceItem`, `EvidenceUnavailable`; validators copy bbox/source/confidence; mobile `EvidenceScreen` is mock.

Not in master: highlighted-image generation, EvidenceService, upload API, measurement-evidence capture, purchase proof.

Planned evidence (Legal Metrology **and** label-to-product): original product image, label image, highlighted OCR region, expected value, observed value, measurement evidence, purchase proof, user notes, timestamp, confidence, applicable rule.

Reuse the existing `evidence` table. Do not duplicate it.

---

# 15. Nutrition `[PLANNED]` as an engine

Secondary consumer feature. Schema `NutritionResult` (`available`, optional `payload` dict); table `nutrition_data`; mobile tile → Coming Soon.

Never invent missing values. Use **“Not detected.”** No medical claims.

Planned extractables: calories/energy, protein, carbohydrates, total sugar, added sugar where available, fat, saturated fat, trans fat, fiber, sodium, other available values.

## Multi-product comparison `[IMPLEMENTED — uncommitted]` (Phase 13)

Scan **current** products A, B, C. Compare calories, sugar, added sugar, protein, fiber, sodium, fat, saturated fat, trans fat, carbohydrates.

User priorities (examples): lower sugar, higher protein, higher fiber, lower sodium, lower saturated fat.

Use a **deterministic, explainable** ranking: “Product B ranks highest based on the user's selected parameters,” with why (lowest sugar, highest protein, higher fiber, higher calories). Never say “Product B is the healthiest.” No medical claims. Keep the UI simple. Do not build a massive recommendation engine.

This is **current A vs current B vs current C**. It is **not** historical SKU change detection.

## 15.1 Comparison engine — current implementation (uncommitted working tree)

Built as an **in-process, deterministic, LLM-free** domain engine beside `compliance/`, in the same spirit as the legal core: pure functions, `Decimal` arithmetic, fixture-tested, no FastAPI/OCR/SQLAlchemy inside. **Uncommitted working-tree state — untracked/modified files on no commit (see the banner at the top and §33), no HTTP endpoint, no DB persistence.** It consumes *already-extracted* nutrition values (it does not read images or call the OCR/nutrition extractors, which are still `[PLANNED]`).

### Files

```text
backend/app/comparison/
  __init__.py         package marker
  units.py            deterministic unit normalisation
  scoring.py          scoring + ranking + explanation  (public entry point)
backend/app/schemas/comparison.py   request + result Pydantic contracts
backend/tests/comparison/
  test_comparison_schemas.py   27 tests
  test_comparison_units.py     28 tests
  test_comparison_scoring.py   20 tests
```

Enums added to `app/core/enums.py` (appended; nothing existing changed): `NutritionParameter` (CALORIES, SUGAR, ADDED_SUGAR, PROTEIN, CARBOHYDRATES, FAT, SATURATED_FAT, TRANS_FAT, FIBER, SODIUM), `ParameterDirection` (LOWER_BETTER, HIGHER_BETTER), `NutritionBasis` (PER_100G, PER_SERVING, UNKNOWN), `ComparisonPriority` (ten `LOWER_*` / `HIGHER_*` values), `ComparisonOutcome` (RANKED, TIED, COULD_NOT_RANK), `ComparisonStatus` (COMPLETED, INSUFFICIENT_DATA). The nine comparison schemas are re-exported from `app/schemas/__init__.py`.

### Public API

```python
from app.comparison.scoring import score_comparison   # ComparisonRequest -> ComparisonResult
from app.comparison.units import normalize_value, normalize_input, canonical_unit_for
```

`score_comparison(request)` is the single entry point. It performs no I/O, calls no model, never mutates the request, and never raises for bad *data* (invalid weights are rejected earlier by the request schema).

### Pipeline

```text
raw values -> unit normalisation -> per-parameter min-max -> user weights
           -> weighted score -> ranking -> explanation
```

**Direction (fixed per parameter; the `LOWER_`/`HIGHER_` prefix on `ComparisonPriority` is the source of truth, mirrored by `PRIORITY_SPEC` in `scoring.py`):**

- LOWER_BETTER: calories, sugar, added sugar, carbohydrates, fat, saturated fat, trans fat, sodium
- HIGHER_BETTER: protein, fiber

**Per-parameter normalisation — relative min-max over only the products with a comparable value for that parameter** (no fixed health thresholds; the repository defines none):

```text
higher-is-better:  score = (value - min) / (max - min)
lower-is-better:   score = (max - value) / (max - min)
max == min         -> 0.5   (neutral; the parameter differentiates no one)
```

**Weighting and final score, per product, over only its available parameters `A`:**

```text
effective_weight(p)      = raw_weight(p) / sum(raw_weight(q) for q in A)   # sums to 1
weighted_contribution(p) = normalized_score(p) * effective_weight(p)
final_score              = sum(weighted_contribution(p) for p in A)        # quantised to 6 dp
```

### Missing values (never invented, never zero)

A parameter a product did not declare is `NOT_DETECTED` (the project's existing convention — there is **no** `MISSING` status). Such a parameter is **dropped from that product's `A`**; its remaining weights re-normalise so they still sum to 1. The product is therefore neither rewarded (no artificial best) nor penalised (no artificial worst). Missingness is surfaced per product via `missing_parameters` and `coverage`. A parameter comparable for **fewer than two** products cannot differentiate anyone and is excluded from the whole comparison, reported in `excluded_parameters` with a reason.

A **declared** value that cannot be parsed is treated the same way, not as an error: an unrecognised or dimensionally-wrong unit (`UNSUPPORTED_UNIT`, e.g. sugar in `cups` or `kJ`) or an invalid magnitude (`INVALID_VALUE`, e.g. negative or non-finite) is not `is_comparable`, so it is dropped from that product's `A` exactly like `NOT_DETECTED`. The difference is visibility: an unparseable declared value also appends a message to that product's `ProductComparisonResult.warnings`, whereas a genuinely undeclared (`NOT_DETECTED`) value is silent. Because the two-product threshold counts only comparable values, a bad unit on one product can also push a whole parameter into `excluded_parameters`.

### Determinism & ranking

All arithmetic is `Decimal`; scores quantise to 6 dp (also the tie-equality threshold). Ranking is standard competition ranking (ties share a rank); display order breaks ties by request order, so repeated runs on the same request are byte-identical. No randomness, no clock.

### Output shape (`ComparisonResult`)

Maps to the conceptual `{ rankings, winner, criteria, explanation }` as follows:

| Conceptual | In `ComparisonResult` |
| --- | --- |
| rankings | `ranking: list[RankEntry]` (rank, product_id, product_name, score) |
| winner | `ranking[0]` and named in `explanation` (no dedicated `winner` field yet) |
| criteria | `priorities_used: list[PriorityWeight]` + `active_parameters` |
| explanation | top-level `explanation: str` + per-product `highlights: list[str]` |

Also present: `status`, `excluded_parameters`, `disclaimer` (informational, always set). Each `ProductComparisonResult` carries `product_id`, `product_name`, `rank`, `score`, `outcome` (RANKED/TIED/COULD_NOT_RANK), `coverage`, `parameter_scores`, `available_parameters`, `missing_parameters`, `highlights`, `warnings`. Each `ParameterScore` exposes the full arithmetic: `canonical_value`, `unit`, `status`, `included`, `normalized_score`, `weight`, `effective_weight`, `weighted_contribution`, `note`. **Note on `warnings`:** data-quality warnings surface **per product** on `ProductComparisonResult.warnings`; the top-level `ComparisonResult.warnings` field exists in the schema but `score_comparison` does not currently populate it, so it is always `[]` today.

**Result language is enforced:** the top product "ranks highest based on your selected parameters (…)"; the engine never says "healthiest" and makes no medical claims.

### What is done vs. what remains

Done (Phases A–E): repository inspection, module design, schemas, unit normalisation, and the deterministic scoring + ranking + top-level explanation, all tested (75 tests, all passing).

**Remaining / deferred (the owner's declared next prompt):**

1. **Richer explanations** — per-product *concise* natural-language sentences and **trade-off** phrasing ("Product B ranks higher overall because it has lower sugar and higher protein, although Product A has lower calories"). Today the engine emits a single top-level `explanation` sentence plus per-product `highlights` (e.g. "Lowest sugar of the compared products"); the sentence-level per-product + trade-off generation is not yet built.
2. **Basis safety** — `ComparisonProductInput.basis` (PER_100G / PER_SERVING / UNKNOWN) exists but scoring does **not** yet reject mixing bases; callers must pass a shared basis. A guard is a good next addition.
3. **HTTP API** — no `POST /api/v1/comparison`; `score_comparison` is ready to wire behind one.
4. **Persistence** — `comparison_sessions` / `comparison_items` tables still do not exist (see §17); the engine is stateless and needs neither to run.
5. **Commit & integration** — the engine is **uncommitted** (untracked/modified files, on no commit — see the banner and §33), so the first git step is to commit `app/comparison/`, `app/schemas/comparison.py`, `tests/comparison/` and the `enums.py` / `schemas/__init__.py` edits. Then connect real nutrition-extraction output to `NutritionValueInput`, and merge into `main`.

### Running the tests

```bash
cd backend
python -m pytest tests/comparison/        # 75 tests
```



---

# 16. Ingredients `[PLANNED]` as an engine

Schema `IngredientItem` today: `name`, optional `raw_text`. Table `ingredients`. Coming Soon tile.

Planned: ingredient name, simple explanation, informational flag, confidence/source. Informational language only. No unsupported medical claims. Do not call a product “dangerous” from a list.

---

# 17. Database `[IMPLEMENTED]` schema

PostgreSQL only (SQLAlchemy 2 + psycopg). SQLite is not supported. `DATABASE_URL` must be `postgresql+psycopg://...` (`postgresql://` is rewritten). Alembic head: `0003_legal_rule_traceability`.

| Table | Purpose |
| --- | --- |
| `users` | `display_name`, `role` (default `INSPECTOR`), optional unique `email`. No password |
| `products` | `name`, `category`, optional `brand` |
| `product_images` | generated `storage_path`; do not use `original_filename` as a path |
| `inspections` | status, optional confidence, `inspected_at`, warnings, `is_demo` |
| `declarations` | per-inspection field/value/status/bbox |
| `nutrition_data` | optional 1:1 payload |
| `ingredients` | optional list |
| `legal_rules` | versioned rules |
| `violations` | potential findings (not a legal verdict) |
| `evidence` | optional artefacts |
| `reports` | PDF metadata `PENDING` / `READY` / `FAILED` |

Inspection children cascade from inspection. Product delete is **RESTRICT** while inspections exist. No live CRUD API.

**Planned tables (do not exist):** `verification_results`, `verification_checks`, `measurement_observations`, `comparison_sessions`, `comparison_items`.

The comparison engine (§15.1) is currently **stateless** — it scores an in-memory `ComparisonRequest` and requires neither `comparison_sessions` nor `comparison_items` to run. Add those only when persisting comparison history.

When added, reuse existing product/declaration/inspection models. Do not duplicate data. `evidence` already exists.

---

# 18. API

Prefix: `/api/v1`.

**Implemented:**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness (unprefixed copy for supervisors) |
| GET | `/api/v1/health` | Versioned liveness |

Error body: `{ "error": { "code": "...", "message": "...", "details": {} } }`. No stack traces to clients. Codes include `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `HTTP_ERROR`, `INTERNAL_ERROR` (500). CORS off unless `CORS_ORIGINS` is set.

`ScanResponse` is a **future** scan contract in `app/schemas/scan.py`. There is no `POST /scans`.

**Future APIs (not implemented):** `POST /verification`, `POST /verification/quantity`, `POST /verification/count`, `POST /comparison`, `GET /products/{id}/verification`.

`POST /comparison` is not implemented, but its engine is ready: a route can call `score_comparison(ComparisonRequest) -> ComparisonResult` directly (§15.1). Both schemas are already exported from `app/schemas`.

---

# 19. Mobile `[IMPLEMENTED]` mock UI

Root: `mobile/`. Expo SDK **~54.0.0**, React Native **0.81.5**, React **19.1.0**, TypeScript. `expo-localization` + i18next. Locales: `en`, `hi`, `mr`, `bn`, `ta`, `gu`, `te`.

**Not present:** NativeWind, `expo-camera`, API client, working image upload (goes to Coming Soon).

| Screen | Role |
| --- | --- |
| Home | Hero scan, mock stats, recent mock inspections; intelligence tiles → Coming Soon |
| Scan | Camera-frame placeholder; Capture replays a mock inspection |
| Processing | Simulated pipeline steps |
| Evidence | Mock highlighted evidence |
| History | Mock inspections |
| Profile | Language + Coming Soon rows |
| Language | Locale picker (persisted) |
| Coming Soon | Nutrition / ingredients / upload placeholders |

Navigation: tabs Home / Scan / History / Profile + stack for Processing, Evidence, Language, Coming Soon. Types in `mobile/types/inspection.ts` mirror a future camelCase `InspectionResponse`.

## Planned consumer UI (not built)

```text
HOME → SCAN PRODUCT → IMAGE PREVIEW → PROCESSING → PRODUCT OVERVIEW
  → LEGAL / LABEL CHECK → LABEL-TO-PRODUCT VERIFICATION → WHAT WAS VERIFIED?
  → EVIDENCE → NUTRITION → INGREDIENTS → COMPARE PRODUCTS → REPORT / SAVE
```

Primary home should emphasize **Scan Product**, not an inspector dashboard.

Potential future sections: My Scans, Saved Products, Compare, Evidence, Reports, Settings.

Result screen priority: (1) Legal Metrology (2) Label-to-product (3) Evidence (4) Nutrition (5) Ingredients.

Example (not current JSON):

```text
LEGAL LABEL CHECK
✓ MRP detected
✓ Net quantity detected
✓ Manufacturer detected

LABEL-TO-PRODUCT VERIFICATION
Declared: 500 g
Observed: 472 g
Status: Potential Mismatch
Confidence: 94%

[View Evidence]  [Verify Again]
```

Replace historical “what changed?” with **“What was verified?”** / **“What did we verify?”**

Comparison UI `[PLANNED]`: scan A/B/C → compare nutrition → user priorities → simple table + ranking explanation.

---

# 20. Consumer action / complaint scope

Do **not** make LabelGuard a government authority. Do **not** create a fake government complaint system.

The app may eventually provide “What can I do next?” with evidence preservation and general consumer guidance. If official grievance functionality is added later, **direct users to official government channels**.

LabelGuard must not pretend to issue government orders or legal determinations.

---

# 21. Reports and history

PDF generation: `[PLANNED]` (`reports` table only). History: `[PARTIALLY IMPLEMENTED]` (table + mock list). Product fingerprint / barcode / previously inspected SKU: `[FUTURE]` and **not** the core verification story.

---

# 22. Testing `[IMPLEMENTED]` for the legal core

`backend/tests/`. Run from `backend/` with venv: `pytest`. Persistence tests skip if Postgres is down.

Includes: health, errors, logging, schemas, models, database, compliance (engine, validators, rule storage, repository, selection, pipeline, edge cases, inputs/safety, performance). Fixtures: declarations, inspections, rules, validators.

Legal tests use **manual declaration fixtures**. They do **not** require OCR, camera, or a live scan.

No verification-engine tests (module absent). No mobile test suite. This file does not freeze a pass count.

In the local (uncommitted) working tree there are 75 additional comparison-engine tests under `tests/comparison/` (`test_comparison_schemas.py`, `test_comparison_units.py`, `test_comparison_scoring.py`); like the legal tests they use manual fixtures and need no OCR, camera or live scan. They are not committed yet (see the banner), so they will not run in CI or a fresh clone until committed.

---

# 23. Security (actual vs intended)

**Actual:** `.env` gitignored; `DATABASE_URL` is `SecretStr` and must not be logged; log redaction; Pydantic validation; no client stack traces; CORS off by default. **No** auth, **no** upload API, therefore **no** image-size limits or secure-filename handling yet.

**Intended when those features exist:** environment variables, file validation, input validation, image size limits, secure filenames, API validation, password hashing if auth exists, role-based access if auth exists, no secrets in Git. Never put real credentials in source code. `users` currently has **no password column**.

---

# 24. Local development

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# optional: alembic upgrade head; python -m seeds.legal_rules; pytest

cd mobile
npm install
npx expo start --lan
```

Expo Go SDK **54**. Postgres optional for `/health`. OpenAPI: http://127.0.0.1:8000/docs

---

# 25. Roadmap

**Completed in master:** backend foundation phases 1–10 (FastAPI, DB schema, contracts, legal storage, versioning, validators, engine, tests) plus Expo mock UI.

**Phase 11 — `[PLANNED]` — Label-to-Product Verification Engine (NEXT)**  
Expected value extraction, current observation input, quantity/text/count where feasible, confidence, result states, evidence linkage.

**Phase 12 — `[PLANNED]` — Advanced verification**  
Richer checks, identity, more observation types, tighter evidence.

**Phase 13 — `[IMPLEMENTED — uncommitted]` — Multi-product nutrition comparison**  
Deterministic scoring, ranking and top-level explanation built in `app/comparison/` (75 tests), currently **uncommitted in the working tree** (see the banner). Remaining: commit the work, per-product concise + trade-off explanations, basis guard, HTTP API, persistence, and merge to `main`. See §15.1.

**Phase 14 — `[PLANNED]` — Evidence / reporting enhancements**  
Highlights, measurement evidence, reports, saved verification.

**Phase 15 — `[PLANNED]` — Consumer dashboard / history**  
Scans, saved products, comparisons, evidence, reports.

**Also required for a real consumer loop, still `[PLANNED]`:** camera, image quality, OCR, declaration extraction, scan API. These were product phases 5–8 and are **not** done in master.

**`[FUTURE]`:** calibrated measurement, barcode, QR, multilingual expansion beyond current UI locales, offline mode, e-commerce analysis, advanced computer vision, optional local LLM (**explanation only**), professional/enforcement **mode**.

## What not to build as core MVP

Fake government complaint authority; complex government authentication; blockchain; unnecessary microservices; custom model training without evidence of need; massive recommendation engine; social complaint network; payment/refund system; complex authority workflow; historical “what changed vs old SKU” as the primary feature.

---

# 26. Teammate work policy

Some teammates may develop OCR, nutrition, evidence, UI, or computer-vision modules in **separate folders, repos, branches, ZIP files, or local projects**.

Unless that code is **explicitly integrated into this master repository**, it is:

**`[TEAMMATE WORK — NOT INTEGRATED]`**

Do **not** mark it as part of the current application.

In master today, teammate **contracts** exist (`OCRResult`, `NutritionResult`, `IngredientItem`, `EvidenceItem`, comments in `backend/README.md`). Teammate **implementations** of OCR/nutrition/evidence-image/PDF are **not** in this tree.

---

# 27. Team ownership

The project owner / master developer retains:

- overall architecture
- integration
- core Legal Metrology engine
- verification architecture
- shared database contracts
- shared API contracts
- main application integration
- final testing
- conflict resolution
- release readiness

Teammates should work on isolated modules and feature branches (`feature/ocr`, `feature/nutrition`, `feature/evidence`, later `feature/verification`). Do not develop on `main`.

**Suggested future division (assign only after reviewing master):**

| Person | Area |
| --- | --- |
| Teammate 1 | Label-to-product verification submodule |
| Teammate 2 | Multi-product nutrition comparison |
| Teammate 3 | Evidence / reporting / UI support |

Teammates must **not** independently rewrite: core database architecture, shared schemas, authentication, configuration, Legal Metrology rule engine, main application architecture — without coordination.

---

# 28. Integration principles

Prefer: clear interfaces, Pydantic schemas, service functions/classes, API contracts, isolated modules, unit tests, minimal dependencies.

Avoid: duplicate OCR, duplicate business logic, duplicate database models, direct modification of unrelated modules, hard-coded paths, hard-coded URLs, circular imports, hidden global state.

The master developer must be able to replace a teammate implementation later without rewriting the entire application.

## When integrating teammate work later

1. Inspect teammate code.  
2. Compare it with master architecture.  
3. Identify dependencies.  
4. Check API/data contracts.  
5. Copy/integrate **only** the required module.  
6. Adapt interfaces if necessary.  
7. Add tests.  
8. Run existing tests.  
9. Run feature-specific tests.  
10. Test the end-to-end flow.  
11. Only then merge into master.

**Never blindly copy an entire teammate project over the master repository.**

---

# 29. Cursor account safety

The user is developing with a Cursor subscription/account that belongs to **another person**.

This project **must remain independent of that Cursor account**.

Future AI agents **MUST NOT**:

- change Cursor account, settings, or subscription
- connect GitHub to Cursor
- connect external accounts
- modify Git credentials or SSH configuration
- modify GitHub settings
- push code automatically
- change Git remotes
- perform account-level actions

All development must remain **local and repository-based**. The project itself must **not** depend on Cursor. It must remain usable in VS Code, Cursor, another IDE, the command line, and CI/CD.

---

# 30. Git safety

Before any Git operation involving a remote:

```text
git remote -v
```

must be checked.

Never assume the remote is correct. Never push without **explicit** user instruction. Never commit, pull, create branches, or merge unless the user asks.

This document does not authorize Git operations.

---

# 31. Instructions for future AI assistants

1. Read `docs/PROJECT_CONTEXT.md` first.  
2. Inspect the actual repository.  
3. Check implementation status from files.  
4. Never assume planned features are implemented.  
5. Never assume teammate work is integrated.  
6. Identify affected files before coding.  
7. Explain architecture impact.  
8. Make minimal changes.  
9. Avoid unrelated modifications.  
10. Preserve existing working functionality (especially the legal core).  
11. Follow existing API/data contracts.  
12. Write tests for new functionality.  
13. Test integration.  
14. Never silently overwrite working code.  
15. Never change account/settings/Git configuration.  
16. Stop after each major phase and wait for confirmation.

Workflow:

```text
GOAL → CURRENT CODE INSPECTION → FILES TO CHANGE → ARCHITECTURE IMPACT
  → API CONTRACT → DATA CONTRACT → IMPLEMENTATION
  → UNIT TESTS → INTEGRATION TESTS → MANUAL TEST → CONFIRMATION → NEXT PHASE
```

Do not rewrite `ComplianceEngine` into an LLM. Do not invent legal tolerances. Do not add government-complaint theatre. Do not treat historical product comparison as the core feature. Do not claim the camera weighs products.

---

# 32. Known limitations (master)

- No camera, OCR engine, scan API, or verification engine on `main`. A deterministic nutrition-**comparison** engine exists **only as uncommitted local working-tree state** (untracked/modified files, on no commit; no API/DB, no per-product/trade-off explanations yet — see the banner and §15.1)
- Legal engine tested with **manual declarations**
- Mobile is mock; Home still resembles an inspection dashboard
- Prototype 2011 rules only; later amendments not encoded except draft origin
- Size validator missing; CARE seed uses `REQUIRED_DECLARATION`
- Origin rule is DRAFT / UNVERIFIED
- No overall legal percentage
- `users.role` default `INSPECTOR` and FastAPI “inspection platform” copy do not match consumer-first identity
- No auth, PDF, or upload validation

---

# 33. File inventory (master)

**Backend:** `app/main.py`; `api/health.py`, `api/router.py`; `core/config.py`, `enums.py`, `exceptions.py`, `logging_config.py`, `request_logging.py`; `database/` models (`user`, `product`, `inspection`, `declaration`, `nutrition`, `ingredient`, `legal_rule`, `violation`, `evidence`, `report`); `schemas/` (`common`, `ocr`, `declaration`, `product`, `inspection`, `legal_rule`, `validation`, `compliance`, `assessment`, `applicability`, `nutrition`, `ingredient`, `evidence`, `report`, `scan`, `comparison`); `compliance/` (`engine`, `aggregation`, `applicability`, `dates`, `registry`, `repository`, `resolver`, `rule_loader`, `selection`, validators); `comparison/` (`units`, `scoring`) *[**uncommitted** — untracked working-tree files, on no commit, with `tests/comparison/` and `schemas/comparison.py`; must be committed to persist]*; `seeds/legal_rules.py`; migrations `0001_foundation`, `0002_models`, `0003_legal_rule_traceability`.

**Mobile:** `App.tsx`, `navigation/`, screens listed in section 19, `i18n/locales/` (7 files), `data/mockInspections.ts`, `data/mockStatistics.ts`, `theme/index.ts`, `types/inspection.ts`.

**Legal:** `legal-rules/2011/rules.json`, `legal-rules/README.md`, `amendments/README.md`, `sources/README.md`.

**Docs:** this file; `docs/compliance-engine.md`, `compliance-validators.md`, `compliance-testing.md`, `legal-rule-storage.md`, `legal-rule-applicability.md`; `backend/README.md`; root `README.md`.

---

# 34. How to continue

When implementation is requested, the next major build is **Phase 11: Label-to-Product Verification Engine** as a new module beside `compliance/`. Camera/OCR/extraction remain unimplemented and are still required for a real consumer loop.

For the **nutrition-comparison** track (§15.1), the work is currently **uncommitted** (see the banner), so step (0) is to commit `app/comparison/`, `app/schemas/comparison.py`, `tests/comparison/` and the `enums.py` / `schemas/__init__.py` edits. Then the immediate next steps are: (1) per-product concise + trade-off explanations generated from the already-computed values, (2) a shared-basis guard, (3) a `POST /comparison` route over `score_comparison`, then (4) persistence and merge to `main`. Keep it deterministic and LLM-free; do not add a recommendation engine or medical claims.

Until then, this file is the product-direction source; the repository is the implementation source.

---

# 35. Phase 11 status — Integration contracts & shared data architecture `[IMPLEMENTED]`

Phase 11 as executed established the **typed data contracts and integration interfaces**
that sit *around* the Legal Metrology core. It did **not** build the verification engine,
OCR, or any algorithm — those remain `[PLANNED]` (see section 34). Full reference:
`docs/integration-contracts.md`.

**Delivered (`[IMPLEMENTED]`):**

- New contract package `backend/app/schemas/contracts/`: `detection.py`
  (`ExtractedDeclaration` + `detection_to_declaration_status` adapter), `context.py`
  (`InspectionContext`), `evidence.py` (`EvidenceReference`), `verification.py`
  (`MeasuredValue` / `VerificationInput` / `VerificationResult` — shape only), `nutrition.py`
  (`NutritionValue` / `NutritionFacts`), `product.py` (`ProductProfile`), `scan.py`
  (`ScanResult` aggregate), and `__init__.py` re-exports.
- Additive enums in `core/enums.py`: `DetectionStatus`, `ObservationSource`,
  `VerificationOutcome`, `EvidenceType` — each documents its relationship to the existing
  vocabulary. No existing enum changed.
- `schemas/ingredient.py::IngredientItem` extended with optional fields (backward
  compatible).
- Tests: `tests/contracts/test_integration_contracts.py` (34 tests). Suite now
  **160 passed, 2 skipped** (was 126 + 2). No regressions.

**Key design decisions:**

- The engine's `DeclarationStatus` is locked (DB `CHECK` constraint +
  `database/models/declaration.py` + validators), so the richer extraction vocabulary
  lives in a **separate** `DetectionStatus` mapped DOWN by a tested adapter — matching the
  codebase's existing layer-specific-enum pattern. Not a duplicate status system.
- `CONFIRMED_ABSENT` → `NOT_DETECTED` at confidence `0.95` so the engine's existing
  reliable-absence logic yields `POTENTIAL_NON_COMPLIANCE`; if the label is not marked
  readable it safely degrades to `MANUAL_REVIEW`, never a silent `COMPLIANT`.
- Verification distinguishes **DECLARED vs OBSERVED**, never emits `FRAUD/CHEATING/ILLEGAL`,
  and uses `VerificationOutcome` (not the existing `VerificationStatus`).
- Missing nutrition is `null`/unknown, never `0`.
- `ScanResult` **reuses** `ComplianceAssessment` for the legal verdict — no competing
  verdict type.

**Not changed:** `ComplianceEngine`, validators, resolver, DB models, migrations, and the
`declarations` `CHECK` constraint are untouched. No new tables. Contracts are
persistence-independent. Phase 12 not started.

---

# 36. Phase 12 status — Scan intake, image quality, OpenCV & OCR `[IMPLEMENTED]`

Phase 12 as executed built the **first pipeline segment**
`PRODUCT IMAGE → SCAN INTAKE → IMAGE QUALITY → IMAGE PROCESSING → OCR → OCR CONTRACT`,
stopping at OCR. It produces an image, an image-quality report, and OCR output — and
**nothing else**. No declaration extraction, no Legal Metrology assessment, no rule/engine
change, no DB change, no public `/scan` API. Full reference: `docs/scan-ocr.md`.

**Delivered (`[IMPLEMENTED]`):**

- New package `backend/app/imaging/`: `validation.py` (magic-byte format sniffing,
  size/dimension checks → `AppError`), `intake.py` (`load_scan` → `PreparedImage`: single
  decode, EXIF-upright, `uuid4` scan id), `quality.py` (blur = variance of Laplacian,
  brightness = mean gray, resolution; `classify_quality` → `OK`/`WARNING`/`UNUSABLE`),
  `preprocessing.py` (`ImagePreprocessor`: resize/CLAHE/denoise/opt-in binarize),
  `pipeline.py` (`process_scan(...) -> ScanProcessingResult`).
- New package `backend/app/ocr/`: `provider.py` (`OCRProvider` Protocol + `RawTextRegion`),
  `paddle_adapter.py` (`PaddleOCRProvider` — lazy import, once-per-process engine,
  `available()` probe), `normalization.py` (`to_bbox` / `normalize_region` /
  `build_ocr_response`), `service.py` (`OCRService`, provider failure → `PROCESSING_ERROR`).
- `schemas/imaging.py`: container schemas that **reuse** the Phase 11 `OCRResult` for every
  region and adapt **down** to the Phase 11 `ImageQualityResult`. No second OCR model.
- Additive enums in `core/enums.py`: `ImageQualityStatus`, `BrightnessStatus`,
  `ResolutionStatus`, `OrientationStatus`, `OCRStatus`. No existing enum changed.
- Additive `Settings` fields (all env-tunable, none legal): scan size/formats, image
  min/max dimensions, blur/brightness thresholds, preprocess max dim, OCR languages and
  low-confidence threshold.
- Deps (wheels only): `numpy`, `opencv-python-headless`, `Pillow`. PaddleOCR listed
  **optional/commented** in `requirements.txt` (lazy, install documented).
- Tests: `tests/imaging/` + `tests/ocr/` (67 tests, OCR mocked, images generated
  in-memory). Suite now **227 passed, 2 skipped** (was 160 + 2). No regressions.

**Key design decisions:**

- **OCR adapts to the contract, not vice-versa** (spec §6): `PaddleOCR → PaddleOCRProvider
  → RawTextRegion → OCRResult`. Swapping the engine or mocking it touches nothing else.
- **Quality and OCR stay separate signals** (no single global "legal confidence"): an
  `UNUSABLE` image still runs OCR; a good read never overrides the quality verdict.
- **No semantics**: `"MRP ₹50"` is kept as a string; it never becomes a value/field.
  `NO_TEXT_DETECTED` ≠ missing declaration; OCR failure ≠ non-compliance (spec §19/§20/§23).
- **PaddleOCR deferred, not forced**: heavy + downloads models at runtime, so it is loaded
  lazily behind a Protocol; the app and the whole test suite run without it. No system-level
  changes (Docker/Hyper-V/services) were made.
- **Original preserved**: input bytes are never mutated or written; all processing is on
  copies. Format is decided by magic bytes, never the filename.

**Not changed:** `ComplianceEngine`, validators, resolver, all Phase 11 contracts, DB
models, migrations, and the `declarations` `CHECK` constraint are untouched. No new tables,
no migrations, no new production API endpoints. Declaration extraction (Phase 15), Legal
Metrology integration (Phase 16), and verification (Phase 17) are **not started**.

---

# 37. Phase 13 status — Multi-product nutrition comparison `[IMPLEMENTED]`

Phase 13 (merged via PR #1, commit `b973907`) adds a **self-contained** capability to
**rank multiple already-scanned products** by their nutrition. It is not part of a single
`ScanResult`: a single scan carries `nutrition: NutritionFacts | None` (missing = `None`,
never zero), while comparison operates over several such panels. Package
`backend/app/nutrition/comparison/`, its own endpoint `POST /nutrition/compare`. Full
reference: `docs/nutrition-comparison.md`.

**Not changed:** the Legal Metrology engine, validators, resolver, rules, DB, and the
`declarations` `CHECK` constraint. The later scan pipeline (Phases 15–19) reaches this
feature only through an adapter boundary and never rebuilds the comparator.

---

# 38. Phase 15 status — Declaration extraction `[IMPLEMENTED]`

Phase 15 built the pipeline segment **between OCR and the engine**:
`OCRResult[] → normalise → per-field extractors → ExtractionResult → ExtractedDeclaration[]`.
It decides *what a region says*, never *what it means legally* — deterministic only, no
LLM, no external lookup, no verdict. Full reference: `docs/declaration-extraction.md`.

**Delivered (`[IMPLEMENTED]`):**

- New package `backend/app/extraction/`: `normalization.py` (NFKC, Devanagari digits,
  explainable OCR-confusion detection, unit/month canonicalisation — pure helpers),
  `extractors.py` (one deterministic extractor per field: keyword anchoring, regex,
  unit/date normalisation, spatial proximity, OCR confidence), `service.py`
  (`DeclarationExtractor` / `extract_declarations`).
- New contracts `backend/app/schemas/extraction.py`: `DeclarationCandidate` /
  `FieldExtraction` / `ExtractionResult`, which **preserve every candidate** and adapt
  DOWN to the Phase 11 `ExtractedDeclaration` (mirroring `RawTextRegion → OCRResult`).
- Tests: `tests/extraction/` (**38 tests**). Suite now **330 passed, 2 skipped**
  (was 292 + 2). No regressions.

**Key design decisions:**

- **Three confidences kept separate:** OCR confidence, extraction confidence, legal
  assessment. `extraction_confidence = clamp(ocr_confidence × pattern_weight)`;
  `DETECTED_CONFIDENCE_THRESHOLD = 0.6` mirrors the engine's `UNCERTAIN_CONFIDENCE_MAX`
  (asserted by a test) without importing the compliance package.
- **`"MRP ₹5O"` → `UNCERTAIN`** with **both** the as-read `"5O"` and corrected `"50"`
  candidates preserved (`raw_text` kept); a number is never silently rewritten. Two-digit
  years are `UNCERTAIN` (`ambiguous_year`) for the same reason.
- Emits **only `DETECTED` / `UNCERTAIN`**; a field with no candidate is **omitted**, never
  a fabricated absence — "not detected in this scan" ≠ "absent from the product".
- Canonical net-quantity units are a subset chosen so a `DETECTED` value is always
  re-parseable by the engine's `parse_quantity` (asserted by a test); an unrecognised unit
  is kept low-confidence for manual review, not dropped.

**Not changed:** `ComplianceEngine`, validators, resolver, DB models, migrations, the
`declarations` `CHECK` constraint. No new tables, no API endpoint.

---

# 39. Phase 16 status — Legal Metrology integration `[IMPLEMENTED]`

Phase 16 bridges Phase 15 extraction to the existing engine via an **adapter**, not a
second engine: `ExtractionResult → Declaration[] → ComplianceEngine.evaluate →
ComplianceAssessment` (the engine's own output, returned unchanged). Full reference:
`docs/scan-pipeline.md` §2.

**Delivered (`[IMPLEMENTED]`):**

- New module `backend/app/pipeline/legal.py`: `assess_extraction`,
  `declarations_for_engine` (reuse the existing `ExtractedDeclaration.to_declaration`
  mapping; `NOT_APPLICABLE` dropped — applicability is the resolver's job).
- Tests: `tests/pipeline/test_pipeline_legal.py` (**8 tests**). Suite now **338 passed,
  2 skipped**. No regressions.

**Key design decisions:**

- **One verdict system.** No legal rule re-implemented, no parallel verdict vocabulary.
- **`label_readable` is the single lever** for "not detected ≠ omission": defaulted to
  `None` (unknown) and **never inferred from per-field OCR confidence**. The engine's
  `presence_outcome` flags a missing required field as `POTENTIAL_NON_COMPLIANCE` only when
  `label_readable is True`, else `MANUAL_REVIEW` — so a single OCR miss is never mistaken
  for an omission, yet a genuine omission still surfaces when the label is known-legible.
- Preserves: OCR failure ≠ absent; low confidence ≠ non-compliance; not-detected ≠
  omission; potential non-compliance / manual review are never "fraud".

**Not changed:** the engine, validators, resolver, rules, DB, migrations, the `CHECK`
constraint. No new tables, no API endpoint.

---

# 40. Phase 17 status — Label-to-product verification `[IMPLEMENTED]`

Phase 17 compares a value **declared on the label** against a value **observed in the
SAME captured image**. The current image is the **only** evidence source — no external
database, marketplace, or web lookup. Full reference: `docs/scan-pipeline.md` §3.

**Delivered (`[IMPLEMENTED]`):**

- New module `backend/app/pipeline/verification.py`: `verify`, `verify_one`,
  `measured_value_from_text`, over the existing `VerificationInput`/`VerificationResult`
  contract and the existing `VerificationOutcome` vocabulary.
- Tests: `tests/pipeline/test_pipeline_verification.py` (**11 tests**). Suite now
  **349 passed, 2 skipped**. No regressions.

**Key design decisions:**

- **Never FRAUD/CRIMINAL.** A difference is `POTENTIAL_MISMATCH` ("to verify, not a
  determination of wrongdoing"); mapping is MATCH / POTENTIAL_MISMATCH / MANUAL_REVIEW
  (units not comparable) / COULD_NOT_VERIFY (no observation or image too weak).
- **Image degradation must not manufacture a mismatch.** Blur/rotation/scale/lighting/
  compression/distance arrive as low `observation_confidence`; below
  `OBSERVATION_CONFIDENCE_MIN = 0.6` the result is `COULD_NOT_VERIFY`. No numeric tolerance
  is invented (float-hygiene only); cross-dimension units → `MANUAL_REVIEW`.
- **Physical-quantity limitation:** a camera cannot measure real mass/volume; for
  `net_quantity` the check is declared-printed vs visible-printed only, and every such
  result appends a caveat pointing to a calibrated measurement.

**Not changed:** the engine, validators, resolver, rules, DB, migrations, the `CHECK`
constraint. No external calls anywhere. No new tables, no API endpoint.

---

# 41. Phase 18 status — Evidence & consumer guidance `[IMPLEMENTED]`

Phase 18 assembles a consumer-facing `ConsumerGuidance` narrative from an existing
`ComplianceAssessment` (+ optional Phase 17 verification). It is a **presentation layer**:
it re-reads verdicts, echoes `assessment.status`, and invents no verdict or severity. Full
reference: `docs/scan-pipeline.md` §4.

**Delivered (`[IMPLEMENTED]`):**

- New module `backend/app/pipeline/guidance.py`: `build_guidance`.
- New contract `backend/app/schemas/contracts/guidance.py`: `ConsumerGuidance`,
  `GuidanceItem` (`{issue, finding_kind, severity, source_reference, detail,
  recommended_evidence, next_steps, limitations}`) — reusing the existing
  `EvidenceReference`.
- Additive enums in `core/enums.py`: `Severity`, `FindingKind`.
- Tests: `tests/pipeline/test_pipeline_guidance.py` (**10 tests**). Suite now **359 passed,
  2 skipped**. No regressions.

**Key design decisions:**

- The five mandated sections — **WHAT WE FOUND / WHY IT MATTERS / WHAT IS UNCERTAIN / WHAT
  EVIDENCE TO KEEP / WHAT YOU CAN DO NEXT** — are always populated, including the all-clear
  case. Violations → `POTENTIAL_NON_COMPLIANCE` items; manual review and every
  verification caveat → `MANUAL_REVIEW` items with notes carried verbatim into
  `limitations`; `MATCH`/`NOT_APPLICABLE` produce no item.
- **LabelGuard claims no action.** The disclaimer states it has not contacted any seller or
  authority and has filed no complaint; `next_steps` are consumer-owned suggestions. There
  is **no government-submission code**. A test forbids `fraud/counterfeit/illegal/…` and any
  "we filed / reported to the authority" phrasing.

**Not changed:** the engine, validators, resolver, rules, DB, migrations, the `CHECK`
constraint. All new fields additive with defaults.

---

# 42. Phase 19 status — Unified scan result & orchestration `[IMPLEMENTED]`

Phase 19 orchestrates the earlier phases into the existing `ScanResult` contract via
`run_scan`, a **coordinator** (not a new engine). Full reference: `docs/scan-pipeline.md`
§5.

**Delivered (`[IMPLEMENTED]`):**

- New module `backend/app/pipeline/orchestrator.py`: `run_scan` — five isolated stages
  (extraction → legal → verification → guidance → nutrition), each `try/except` so a
  failure/missing input is recorded, never fatal.
- Additive on `schemas/contracts/scan.py`: `ScanStageStatus` + `ScanResult.guidance` and
  `ScanResult.stages` (both default empty → every earlier construction still valid).
- Additive enum `StageOutcome` (`COMPLETED`/`SKIPPED`/`FAILED`) in `core/enums.py`.
- Tests: `tests/pipeline/test_pipeline_orchestrator.py` (**8 tests**). Suite now
  **367 passed, 2 skipped**. No regressions.

**Key design decisions:**

- **Partial results, never a crash.** A `ScanResult` always returns; coverage and errors
  are surfaced in `stages` (a `ScanStageStatus` each) and `warnings`.
- **Failure is never an implied pass.** A skipped/failed legal stage leaves
  `legal_assessment = None`, never `COMPLIANT`.
- **Legal is independent of nutrition** (missing = `None`, never zero); a single scan
  carries its `NutritionFacts` through unchanged — the Phase 13 comparator is **not**
  rebuilt here.
- **Endpoint decision (deliberate):** `POST /api/v1/scan` was **not** added. `run_scan`
  needs a live `ComplianceEngine` (DB/seed rules, not JSON-serializable) and OCR from
  images; a real endpoint requires the full image→OCR→rule-loading→engine wiring, beyond
  this milestone, and would ship a half-wired placeholder. The orchestration **function**
  is the delivered substance; the spec permits adding an endpoint "only if the architecture
  requires it, with no duplicate endpoints." Recorded here as an explicit decision.

**Not changed:** the engine, validators, resolver, rules, DB, migrations, the `CHECK`
constraint, and the Phase 13 comparator. No new tables, no migrations, no new production
API endpoint.

**Phase sequence complete through Phase 19. Per the project's gating rule, no further
feature phases are begun without explicit authorisation.**
