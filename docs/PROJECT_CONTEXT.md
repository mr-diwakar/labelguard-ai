# LabelGuard AI — Master Project Context

**Tagline:** Scan. Verify. Understand.

This file is the single technical context for LabelGuard AI. A future developer or AI assistant should read this file, then inspect the repository, before changing code.

**Authoritative source of truth:** the files in this workspace. If this document disagrees with the code, trust the code. This file was written from a local repository inspection. Planned features are not claimed as implemented.

---

## 1. What the project is

LabelGuard AI is an **AI-assisted Legal Metrology compliance and product-label intelligence platform** for packaged commodities in India.

It is a decision-support / inspection system. It is **not** a legal authority, a court, or a certificate of compliance.

Type (SIH wording):

> AI-Powered Legal Metrology Compliance & Product Label Intelligence Platform

It must **not** be described primarily as a nutrition scanner, food scanner, chatbot, or generic product scanner.

---

## 2. Why it exists

Packaged commodities sold in India must carry certain declarations under the Legal Metrology (Packaged Commodities) Rules, 2011 (identity, net quantity, MRP, dates where applicable, consumer-care contact, and others). Checking those declarations by hand is slow and easy to get wrong.

LabelGuard’s purpose is to:

1. Help an inspector or consumer **capture a label**.
2. **Extract** structured declarations (eventually via OCR).
3. Run a **deterministic Legal Metrology rule engine** on that structured data.
4. Produce an **automated assessment** with evidence references and a recommendation for manual verification when needed.

---

## 3. SIH problem statement

| Item | Value |
| --- | --- |
| Hackathon | Smart India Hackathon 2026 |
| Problem statement | **26034** |
| Problem | Software system to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels |
| Organization | Ministry of Consumer Affairs, Food & Public Distribution |
| Department | Department of Consumer Affairs |
| Domain | Legal Metrology / packaged commodities |

Official Legal Metrology landing page:

https://consumeraffairs.gov.in/pages/legal-metrology-act

Official consolidated publication of the 2011 Rules with amendments (DoCA):

https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/Book_on_Legal_Metrology_Packaged_Commodities_Rules%2C2011_with_all_amendments_whatsnews.pdf

Do **not** invent legal requirements from blogs or unofficial sites.

---

## 4. Primary USP

**Primary USP:** AI-assisted Legal Metrology compliance inspection for Indian packaged commodities.

**Secondary value:** nutrition and ingredient intelligence (not the core demo; engines not implemented).

```text
                    LABELGUARD AI
                          |
             +------------+------------+
             |                         |
        PRIMARY USP              SECONDARY VALUE
             |                         |
    LEGAL METROLOGY          NUTRITION + INGREDIENT
      COMPLIANCE                 INTELLIGENCE
             |
       +-----+-----+
       |     |     |
      OCR   RULE   EVIDENCE
            ENGINE
             |
          REPORTS
```

OCR, evidence highlighting, and PDF reports **support** the legal engine. They are not the USP by themselves.

---

## 5. Target users

From `UserRole` in `backend/app/core/enums.py`:

- `INSPECTOR` (default on the `users` table)
- `CONSUMER`
- `ADMIN`

Authentication, login screens, and role enforcement are **not implemented**. The mobile UI is a consumer/inspector demo shell with mock inspections.

---

## 6. Complete architecture (intended vs actual)

### Intended product pipeline

```text
Product image
  → image quality / preprocessing
  → OCR
  → structured declarations
  → product classification
  → applicable rule resolution (date + category)
  → deterministic validators
  → compliance assessment
  → evidence
  → storage + PDF report
```

Secondary (planned): nutrition extraction; ingredient extraction.

### Actual architecture in this repository

```text
MOBILE (Expo / React Native, mock data)
        ✗ not wired to API yet

FASTAPI (local)
  GET /health, GET /api/v1/health only
        │
        ├── PostgreSQL schema + Alembic (tables exist; API does not CRUD yet)
        │
        └── LEGAL METROLOGY CORE (in-process, testable without OCR/DB)
              Rule JSON → repository/loader
              → version + applicability
              → validators
              → ComplianceEngine
              → ComplianceAssessment
```

There is **no** `app/ai/`, **no** OpenCV, **no** PaddleOCR, **no** scan orchestrator, **no** PDF generator, and **no** live mobile↔API client in source.

Conceptual target (not all boxes exist as code):

```text
                 MOBILE APP
            React Native + Expo
                      │
                      ▼
                 FASTAPI API
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
    OpenCV        PaddleOCR       PostgreSQL
    (planned)     (planned)      (schema ready)
                      │
                      ▼
              INFORMATION EXTRACTION (schema only)
                      │
                      ▼
              LEGAL METROLOGY ENGINE (implemented)
                      │
                      ▼
              RESULT / EVIDENCE / PDF (contracts + tables only)
```

---

## 7. Current implementation status

| Feature | Status | Evidence |
| --- | --- | --- |
| FastAPI process | IMPLEMENTED | `backend/app/main.py`; `/health` returns `{"status":"ok"}` |
| Error envelope + request logging | IMPLEMENTED | `app/core/exceptions.py`, `request_logging.py`, secret redaction |
| Config via `.env` | IMPLEMENTED | `app/core/config.py`, `backend/.env.example` |
| PostgreSQL driver + lazy engine | IMPLEMENTED | `app/database/connection.py`; API starts without DB |
| Alembic migrations | IMPLEMENTED | `0001_foundation`, `0002_models`, `0003_legal_rule_traceability` |
| 11 application tables | IMPLEMENTED (schema) | `app/database/models/` |
| Pydantic integration contracts | IMPLEMENTED (contracts) | `app/schemas/` — tests use them; most are not HTTP |
| Legal rule JSON + seed | IMPLEMENTED | `legal-rules/2011/rules.json`, `python -m seeds.legal_rules` |
| Rule repository / loader | IMPLEMENTED | `repository.py`, `rule_loader.py` |
| Rule versioning + applicability | IMPLEMENTED | `selection.py`; overlap → `OVERLAP` |
| Deterministic validators | IMPLEMENTED | `app/compliance/validators/` + registry |
| Compliance engine | IMPLEMENTED | `engine.py`; in-memory resolver in tests |
| Scan / OCR HTTP API | NOT IMPLEMENTED | `ScanResponse` schema exists; no route |
| PaddleOCR / OpenCV | NOT IMPLEMENTED | not in `requirements.txt`; no source matches |
| Declaration extraction from images | NOT IMPLEMENTED | `Declaration` is a structured contract only |
| Evidence image generation | NOT IMPLEMENTED | table + `EvidenceItem`; no generator |
| PDF reports | NOT IMPLEMENTED | `reports` table + `ReportResult`; no PDF library |
| Nutrition engine | NOT IMPLEMENTED | `NutritionResult` + `nutrition_data` table only |
| Ingredient engine | NOT IMPLEMENTED | `IngredientItem` + `ingredients` table only |
| Authentication | NOT IMPLEMENTED | `users` has no password hash; no auth routes |
| Mobile UI (mock) | IMPLEMENTED | Expo 54 app, navigation, i18n, mock inspections |
| Mobile camera | NOT IMPLEMENTED | no `expo-camera`; Scan is a placeholder |
| Mobile ↔ FastAPI | NOT IMPLEMENTED | no API client; mock data only |
| Product fingerprint / barcode / e-commerce | NOT IMPLEMENTED | not in code |
| Font / mm calibration | NOT IMPLEMENTED | `READABILITY` / `TEXT_FORMAT` enums only |

---

## 8. Backend architecture

Root: `backend/`.

```text
backend/
  app/
    main.py                 FastAPI factory
    api/                    health + versioned router only
    core/                   config, enums, errors, logging
    database/               SQLAlchemy models, lazy engine
    schemas/                Pydantic contracts
    compliance/             legal core (engine/validators do not import FastAPI)
  migrations/               Alembic
  seeds/                    legal rule seed
  tests/
  requirements.txt
  alembic.ini
  pytest.ini
  .env.example
```

There is **no** `app/ai/`, `app/nutrition/` package, `app/evidence/` package, or `app/reports/` package. Those concerns exist as **schemas and tables**.

**Dependency direction (legal core):**

```text
API  →  (future services)  →  ComplianceEngine
                                → RuleResolver
                                → ValidatorRegistry
                                → Validators
```

Validators and `ComplianceEngine` must not import FastAPI, OCR, or SQLAlchemy. Production wiring: `RuleLoader` (session) implements `resolve()` via `select_for_inspection()`. Tests use `StaticRuleResolver`.

Python: README asks for **3.13+**. Tests have been run on **3.14** in this workspace. Virtualenv: `backend/.venv`.

---

## 9. Mobile architecture

Root: `mobile/`. Expo SDK **~54.0.0**, React Native **0.81.5**, React **19.1.0**, TypeScript strict.

**Not present:** NativeWind/Tailwind, Expo Camera, a working image-upload path (Home “upload image” goes to Coming Soon).

**Screens that exist:**

| Screen | Role |
| --- | --- |
| Home | Hero scan, stats, recent mock inspections; intelligence tiles → Coming Soon |
| Scan | Camera frame placeholder; Capture replays a mock inspection |
| Processing | Simulated pipeline steps |
| Evidence | Mock highlighted evidence for a sample inspection |
| History | List of mock inspections |
| Profile | Language entry + Coming Soon rows |
| Language | Locale picker (persisted) |
| Coming Soon | Nutrition / ingredients / upload placeholders |

Navigation: bottom tabs (Home, Scan, History, Profile) + native stack (Processing, Evidence, Language, Coming Soon). Theme tokens in `mobile/theme/index.ts`.

Data: `mobile/data/mockInspections.ts`. Types in `mobile/types/inspection.ts` are written to **mirror** a future FastAPI `InspectionResponse` (camelCase).

---

## 10. OCR architecture

**Status: NOT IMPLEMENTED.**

Planned engine: PaddleOCR. Not installed. No version, language list, CPU/GPU init, or preprocessing code exists.

Teammate-1 **contract** (`app/schemas/ocr.py`):

- `OCRResult`: `text`, `confidence` in `[0, 1]`, `bbox: [x1, y1, x2, y2]` pixels (`x2 >= x1`, `y2 >= y1`)
- `ImageQualityResult`: `usable`, optional `reason`

Mobile evidence overlay uses a **different** box: normalised `x, y, width, height` in `[0, 1]`. A future adapter must convert pixel OCR boxes. That conversion is **not implemented**.

---

## 11. Computer vision architecture

**Status: NOT IMPLEMENTED.**

Intended: file validation, blur, brightness, glare, resolution, orientation, perspective, denoise, contrast, then OCR. None of those steps exist as code.

---

## 12. Information extraction

**Status: NOT IMPLEMENTED as a pipeline.** Structured `Declaration` **is** a contract and a DB table.

`Declaration` (`app/schemas/declaration.py`): `field`, `value`, `confidence`, `source` (`OCR` / `MANUAL` / `SYSTEM`), optional pixel `bbox`, `status`.

Statuses: `DETECTED`, `NOT_DETECTED`, `LOW_CONFIDENCE`, `MANUALLY_VERIFIED`. There is **no** `MISSING` status.

`NOT_DETECTED` means extraction found nothing. It is **not** automatically “legally missing.”

Validator field aliases (application names, not government names) include `manufacturer`, `commodity_name` / `name`, `net_quantity`, date fields, `mrp` / `retail_sale_price`, `consumer_care`, `country_of_origin` (`validators/support.py`).

There is no extractor that turns OCR text into these fields.

---

## 13. Legal Metrology rule engine

**Status: IMPLEMENTED** as an in-process domain service. **Not** exposed as HTTP. **Not** an LLM.

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

Overall statuses (`ComplianceStatus`): `COMPLIANT` | `POTENTIAL_NON_COMPLIANCE` | `MANUAL_REVIEW`.

Validator outcomes (`ValidationOutcome`): `PASS` | `POTENTIAL_NON_COMPLIANCE` | `MANUAL_REVIEW` | `NOT_APPLICABLE`.

`PASS` is **not** inspection `COMPLIANT`.

Aggregation:

```text
POTENTIAL_NON_COMPLIANCE  >  MANUAL_REVIEW  >  COMPLIANT
```

`NOT_APPLICABLE` and `PASS` are not failures. Zero applicable verified rules → `MANUAL_REVIEW`. Missing validator, validator exception, overlapping versions, unverified/draft rules → `MANUAL_REVIEW`, not a violation.

`assessment_confidence` is always `null`. Do not invent an “87% compliant” score.

Explanations use: “Automated assessment”, “potential non-compliance detected”, “manual verification recommended”, “insufficient evidence”, “this is not a legal determination.”

| `validation_type` | Validator |
| --- | --- |
| `REQUIRED_DECLARATION` | `RequiredDeclarationValidator` |
| `MRP_VALIDATION` | `MRPValidator` |
| `NET_QUANTITY_VALIDATION` | `NetQuantityValidator` |
| `DATE_VALIDATION` | `DateDeclarationValidator` |
| `CONSUMER_CARE_VALIDATION` | `ConsumerCareValidator` (seed CARE row is still `REQUIRED_DECLARATION`) |

`CONDITIONAL_REQUIREMENT` (Rule 6(1)(f) size) has **no** validator. If it is applicable, the engine returns `MANUAL_REVIEW` for that rule.

Prototype seed (`legal-rules/2011/rules.json`):

| Code | Source | Type | Verification |
| --- | --- | --- | --- |
| `LM-PC-MFR-001` | Rule 6(1)(a) | REQUIRED_DECLARATION | VERIFIED (excludes packaged food) |
| `LM-PC-NAME-001` | Rule 6(1)(b) | REQUIRED_DECLARATION | VERIFIED |
| `LM-PC-NETQ-001` | Rule 6(1)(c) | NET_QUANTITY_VALIDATION | VERIFIED |
| `LM-PC-DATE-001` | Rule 6(1)(d) | DATE_VALIDATION | VERIFIED (excludes food and cosmetic) |
| `LM-PC-MRP-001` | Rule 6(1)(e) | MRP_VALIDATION | VERIFIED |
| `LM-PC-SIZE-001` | Rule 6(1)(f) | CONDITIONAL_REQUIREMENT | VERIFIED; only when `size_is_relevant` |
| `LM-PC-CARE-001` | Rule 6(2) | REQUIRED_DECLARATION | VERIFIED |
| `LM-PC-ORIGIN-001` | not in the 2011 India Code text used for the set | REQUIRED_DECLARATION | DRAFT / UNVERIFIED |

Internal `rule_code` values are LabelGuard IDs, not government numbers. Seed severity is `UNSPECIFIED`.

---

## 14. Rule versioning

**Status: IMPLEMENTED.**

A version is in force when:

```text
effective_from <= inspection_date
AND (effective_to IS NULL OR inspection_date <= effective_to)
```

Aware datetimes become a **UTC calendar date**. The selector does not use “the latest row.”

Non-overlapping example: A `2021-01-01`–`2024-12-31`, B `2025-01-01`–open → 2023 uses A; 2026 uses B.

**Overlap:** two open windows on the same date → `ApplicabilityDecision.OVERLAP`. Do **not** silently pick the later `effective_from`. The engine returns `MANUAL_REVIEW` plus a warning.

Future windows are not evaluated. Expired windows are not current, but still apply inside their window.

Unique DB key: `(rule_code, source_version, effective_from)`. Never delete historical rows to “update” a rule.

---

## 15. Evidence system

**Status: PARTIALLY IMPLEMENTED** (data model + UI mock + bbox on validation results).

- Table `evidence` (`AVAILABLE` / `UNAVAILABLE` / `FAILED`)
- Schema `EvidenceItem`, `EvidenceUnavailable`
- Validators copy declaration bbox/source/confidence/status
- Mobile `EvidenceScreen` is mock

**Not implemented:** highlighted-image generation, EvidenceService, upload/attach in an API.

---

## 16. Nutrition system

**Status: NOT IMPLEMENTED** as an engine.

Schema `NutritionResult`; table `nutrition_data`; mobile tile → Coming Soon. Legal analysis must work when nutrition is absent. Never invent nutrient values.

---

## 17. Ingredient system

**Status: NOT IMPLEMENTED** as an engine.

Schema `IngredientItem`; table `ingredients`; mobile tile → Coming Soon. Do not diagnose conditions or call a product “dangerous” from ingredients alone.

---

## 18. Database architecture

**PostgreSQL** (SQLAlchemy 2 + psycopg). SQLite is not supported.

The API **starts without** Postgres. First session uses `connect_timeout: 3`. Persistence tests **skip** if Postgres is down.

Alembic head: `0003_legal_rule_traceability`.

| Table | Purpose |
| --- | --- |
| `users` | `display_name`, `role`, optional unique `email`. No password. |
| `products` | `name`, `category`, optional `brand` |
| `product_images` | generated `storage_path`; do not use `original_filename` as a path |
| `inspections` | status, optional confidence, `inspected_at`, warnings, `is_demo` |
| `declarations` | per-inspection field/value/status/bbox |
| `nutrition_data` | optional 1:1 payload |
| `ingredients` | optional list |
| `legal_rules` | versioned rules |
| `violations` | potential findings (not a legal verdict) |
| `evidence` | optional artefacts |
| `reports` | PDF metadata (`PENDING` / `READY` / `FAILED`) |

Inspection children cascade from inspection. Product delete is **RESTRICT** while inspections exist. No live CRUD API yet. `get_db()` exists but is unused by routes.

---

## 19. API architecture

Prefix: `/api/v1`.

| Method | Path | Purpose | Body |
| --- | --- | --- | --- |
| GET | `/health` | Liveness (unprefixed for probes) | `{"status":"ok"}` |
| GET | `/api/v1/health` | Same, versioned | `{"status":"ok"}` |

That is the **entire** HTTP surface. `ScanResponse` documents a future `POST /api/v1/scans` and is **not** registered.

Error envelope:

```json
{ "error": { "code": "NOT_FOUND", "message": "...", "details": {} } }
```

OpenAPI: http://127.0.0.1:8000/docs when the server is running.

CORS: only if `CORS_ORIGINS` is non-empty. Default: no CORS headers.

---

## 20. PDF reports

**Status: NOT IMPLEMENTED.** Table + `ReportResult` only. A failed PDF must not delete the inspection. Future PDFs must state that results are AI-assisted assessments.

---

## 21. Inspection history

**Status: PARTIALLY IMPLEMENTED.** DB tables exist. Mobile History uses **mock** records. No `GET /inspections` API.

---

## 22. Product fingerprinting

**Status: NOT IMPLEMENTED.** No barcode/QR pipeline, no “previously inspected” matching.

---

## 23. Multilingual support

1. **UI translation — IMPLEMENTED for listed locales.** `i18next` + `expo-localization` + AsyncStorage. Locales: **en, hi, mr, bn, ta, gu, te**. Device language at first launch; Profile → Language persists. Kannada, Malayalam, Punjabi are **not** present.
2. **Multilingual label OCR** (e.g. mapping शुद्ध मात्रा → `net_quantity`) — **NOT IMPLEMENTED.**

Engine field names stay English application keys.

---

## 24. Security (actual)

Present:

- `.env` gitignored; `.env.example` documents local defaults
- `DATABASE_URL` as `SecretStr`; logs redact password/token/api_key/database_url
- Pydantic validation (confidence 0..1; no `MISSING`)
- Clients do not receive stack traces
- SQLAlchemy parameterized queries in the rule repository

Not present: password hashing, sessions/JWT, RBAC enforcement, upload size/MIME checks (no upload API).

**Never commit** `.env`, passwords, API keys, tokens, or private keys.

---

## 25. Testing

`backend/tests/`, pytest, `pytest-cov` listed in requirements.

- Unit: validators, parsers, selection
- Integration: resolver + registry + engine (in-memory)
- Domain: `test_pipeline.py`
- Persistence: skipped without Postgres

Covered legal-safety cases include: low-confidence `NOT_DETECTED` is not a violation; confirmed absence can be `POTENTIAL_NON_COMPLIANCE`; historical versions; future/expired; overlap refusal; unverified rules; missing validator; empty applicable set; validator exceptions; determinism.

Mobile has **no** automated test suite.

From `backend/`: `pytest`. Coverage: `pytest --cov=app/compliance`.

---

## 26. Git workflow

Inspected locally:

- Branch: `main`, tracking `origin/main`
- Remote `origin`: `https://github.com/mr-diwakar/labelguard-ai.git`
- Recent commits seen: `initial commit`; `Stable core before teammate integration`

**Before any future push (only if the owner explicitly asks):** run `git remote -v`. Never push to an unknown remote. This file does not authorise push, pull, merge, or credential changes.

Recommended teammate branches: `feature/ocr`, `feature/nutrition`, `feature/evidence` → tests → PR → review → merge. Do not copy teammate folders into this master repo without an explicit integration phase.

---

## 27. Team responsibilities

**Master / architecture (this repo’s legal core and API contracts):** architecture, integration, Legal Metrology engine, database schema, tests, conflict resolution.

**Teammate 1:** OCR / OpenCV / image quality via `OCRResult` / `ImageQualityResult`.

**Teammate 2:** Nutrition / ingredients via `NutritionResult` / `IngredientItem`; must not block legal analysis.

**Teammate 3:** Evidence images / PDF via `EvidenceItem` / `ReportResult`; failure is a warning/status, not a lost inspection.

Do not duplicate OCR init, legal rules, or schemas.

---

## 28. Integration strategy

Intended scan path (not built):

```text
Mobile image → POST scan → quality + OCR → declarations
  → ComplianceEngine.evaluate(...) → persist
  → optional evidence/PDF → InspectionResponse
```

Use `app/schemas/`. Inject `RuleLoader(session)` or `StaticRuleResolver`. No SQL inside validators. No hardcoded production API URLs in mobile without config.

---

## 29. Development phases

**Backend phases actually used in this repository:**

| Phase | Name | Status |
| --- | --- | --- |
| 1 | FastAPI + health | Done |
| 2 | Logging, error envelope | Done |
| 3 | PostgreSQL + Alembic foundation | Done |
| 4 | Application tables | Done |
| 5 | Pydantic contracts | Done |
| 6 | Legal rule storage + seed | Done |
| 7 | Versioning + applicability | Done |
| 8 | Validators + registry | Done |
| 9 | Compliance engine | Done |
| 10 | Testing, hardening, overlap refusal | Done |

A separate **product** sequence (image processing, PaddleOCR, extraction, scan API, evidence, nutrition, mobile integration, PDF) is still ahead. That numbering is **not** the same as backend Phases 1–10.

Do not start the next major product phase without an explicit prompt.

---

## 30. Current development status

The **backend legal core** is the mature piece. Mobile is a visual/i18n prototype. End-to-end integration has not started.

### Currently implemented

- FastAPI health service with structured errors and redacted logs
- PostgreSQL schema + migrations + optional seed
- Versioned legal rules (prototype 2011 set)
- Applicability + historical selection + overlap detection
- Five deterministic validators + registry
- ComplianceEngine + ComplianceAssessment
- Pytest suite for the legal core
- Expo 54 mobile shell with mock Legal Metrology UI and 7 UI languages

### Partially implemented

- Inspection/evidence/report/nutrition/ingredient **tables and contracts** without services
- Mobile history/evidence/scan **screens** without camera or API
- UI i18n without label-language OCR

### In development

No named open backend phase. Next expected product work, when explicitly requested: integration contracts, then OCR/scan wiring.

### Planned

PaddleOCR, OpenCV quality, extraction, scan API, auth, evidence images, PDF, nutrition/ingredient engines, barcode/fingerprint, e-commerce URL analysis, calibrated font measurement.

---

## 31. Known limitations

- No camera, no real OCR, no scan API
- Engine is not persisted through HTTP
- Seed rules are a **prototype** of selected 2011 clauses, not the full Rules plus all amendments
- Country-of-origin row is an unverified draft
- Size rule has no validator
- Consumer-care validator does not certify legal sufficiency of phone/email format
- MRP/quantity/date parsers are structural, not complete unit-law or date-display law
- No overall assessment-confidence methodology
- Postgres is often absent on the Windows machine; persistence tests skip
- Root `README.md` is empty
- `mobile/AGENTS.md` mentions Expo v57 docs while the app is SDK 54 — prefer `package.json`

---

## 32. Future roadmap (MVP first)

**MVP:** Legal Metrology (MRP, net quantity, manufacturer/name, applicable dates, consumer care, confidence, evidence, rule engine) plus platform (mobile, FastAPI, PostgreSQL, history, PDF, English/Hindi).

Do **not** expand nutrition, e-commerce, or extra languages until scan → declaration → engine → assessment is real.

Strongest demo:

```text
Label → detected declaration → applicable rule → potential issue
  → highlighted evidence → recommended manual verification
```

---

## 33. Important engineering principles

1. Do not over-engineer the MVP; no extra microservices.
2. Keep legal rules out of scattered `if mrp_missing` blocks.
3. Keep OCR separate from compliance; keep nutrition separate from legal status.
4. Preserve bounding boxes and per-field confidence.
5. Never invent extracted values.
6. Never turn OCR uncertainty into a violation.
7. Never let an LLM make the final legal decision.
8. Do not claim millimetre text height without calibration.
9. Prefer `MANUAL_REVIEW` when unsure.
10. Environment variables for config; no hardcoded secrets.
11. Smallest safe change; do not overwrite working code for style.
12. Test the legal core without Postgres/OCR; keep DB tests skippable.

---

## 34. Important legal-design principles

- Official DoCA / India Code sources only for new rules.
- Do not invent rule numbers or applicability.
- Only `ACTIVE` + `VERIFIED` rows are production law in the engine.
- Historical inspections must remain reproducible after later amendments.
- Output is an **automated assessment**, never “this product is legal/illegal.”

---

## 35. AI safety principles

When AI is added, it may detect, OCR, extract, classify, normalise, and explain. The Legal Metrology engine stays deterministic.

If the image is blurry and MRP cannot be read:

- Wrong: “MRP missing” as a violation.
- Right: “MRP could not be reliably verified. Manual verification recommended.”

---

## 36. Local-development instructions

Work only in this local workspace. Do not modify Cursor account, Origin, Cloud Agents, or GitHub settings as part of coding.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health: `curl http://127.0.0.1:8000/health`

Optional Postgres:

```powershell
alembic upgrade head
python -m seeds.legal_rules
pytest
```

### Mobile

```powershell
cd mobile
npm install
npx expo start --lan
```

(`npm install` — verify before use if `node_modules` already exists.)

Expo Go must match **SDK 54**. Phone and PC on the same Wi-Fi. URL form: `exp://<LAN-IP>:8081`.

### System dependencies

- Python 3.13+ (3.14 observed)
- Node.js for Expo (version not pinned in-repo)
- PostgreSQL 16+ optional for API liveness, required for migrations/seed
- **Not required for the current core:** PaddleOCR, OpenCV, CUDA, Ollama

---

## 37. How a future developer should continue

1. Read this file.
2. Inspect `backend/app/compliance/`, `mobile/`, `legal-rules/`, `docs/`.
3. Treat planned features as **missing** until runtime code and tests exist.
4. Next logical product step after backend Phase 10: **integration contracts** (scan API shape, extraction interface, wiring `RuleLoader`) — only when explicitly requested.
5. Then: OCR adapter, mobile client, evidence/PDF.

Do not rewrite the engine to call an LLM. Do not invent amendments in `rules.json`.

---

# File inventory (concise)

### Backend

| Path | Purpose | Status |
| --- | --- | --- |
| `app/main.py` | FastAPI app | Live |
| `app/api/health.py` | Health routes | Live |
| `app/core/*` | Config, enums, logging, errors | Live |
| `app/database/*` | Models + lazy engine | Schema live |
| `app/schemas/*` | Contracts | Live |
| `app/compliance/engine.py` | Orchestration | Live |
| `app/compliance/selection.py` | Versions + applicability | Live |
| `app/compliance/validators/*` | Deterministic checks | Live |
| `app/compliance/registry.py` | Type → validator | Live |
| `seeds/legal_rules.py` | Idempotent seed | Live |
| `migrations/versions/0001–0003` | Schema | Live |

### Mobile

| Path | Purpose | Status |
| --- | --- | --- |
| `App.tsx`, `navigation/` | Shell | Live mock |
| `screens/*` | UI listed above | Live mock |
| `i18n/` | 7 locales | Live |
| `data/mock*.ts` | Demo inspections | Live mock |
| `types/inspection.ts` | Future API shape | Contract |

### Legal rules

| Path | Purpose |
| --- | --- |
| `legal-rules/2011/rules.json` | Prototype clauses |
| `legal-rules/README.md` | How to add amendments |
| `legal-rules/sources/`, `amendments/` | Notes / placeholders |

### Tests

| Path | Purpose |
| --- | --- |
| `tests/test_health.py` and related | Phases 1–5 |
| `tests/compliance/test_rule_*.py` | Storage, selection |
| `tests/compliance/test_validators.py` | Phase 8 |
| `tests/compliance/test_engine.py` | Phase 9 |
| `tests/compliance/test_pipeline.py` and related | Phase 10 |
| `tests/fixtures/` | Shared fixtures |

### Other docs

`docs/legal-rule-storage.md`, `legal-rule-applicability.md`, `compliance-validators.md`, `compliance-engine.md`, `compliance-testing.md`, `backend/README.md`.

### Dependencies (current phases)

Python: FastAPI, Uvicorn, Pydantic, pydantic-settings, SQLAlchemy, Alembic, psycopg, pytest, pytest-cov, httpx.

Node: Expo 54, React Navigation, AsyncStorage, i18next, expo-localization, RN screens/safe-area, RN web.

No PaddleOCR, OpenCV, reportlab, camera SDK, or LLM client.

---

# Account and repository safety

This project must stay independent of whoever owns a Cursor subscription.

- Do **not** change Cursor account, team, org, billing, privacy, cloud agents, or indexing as part of development.
- Do **not** connect or disconnect GitHub inside Cursor, create remotes, or upload the repo to an external AI service without explicit permission.
- GitHub ownership stays with the human project owner. An origin URL is **not** permission to push.
- Before any future push: `git remote -v`. Never push to an unknown remote.
- Do not create SSH keys or change git config unless the owner explicitly asks.
- Do not commit `.env`.

Remote observed at inspection time: `origin` → `https://github.com/mr-diwakar/labelguard-ai.git`. Treat as **information only**.

---

# Instructions for future AI assistants

Before changing code:

1. Read `docs/PROJECT_CONTEXT.md`.
2. Inspect the actual repository.
3. Determine current implementation status from files, not from chat memory.
4. Do not assume planned features are implemented.
5. Identify dependencies (`backend/requirements.txt`, `mobile/package.json`).
6. Explain which files will change and why.
7. Make the smallest safe change. Do not recreate working files.
8. Test the change (`pytest` for the backend legal core).
9. Report exactly what changed.
10. Do not modify unrelated files (especially `mobile/` during backend-only work, and vice versa).

For major phases:

- Explain the goal
- List files
- Give commands
- Implement
- Test
- Explain output
- **Stop for confirmation**

Do not silently continue into the next major phase.

Work **only** in this local LabelGuard workspace unless the user explicitly expands the scope.
