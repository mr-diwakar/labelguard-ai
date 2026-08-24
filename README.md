# LabelGuard AI

## AI-Powered Legal Metrology Compliance & Product Label Intelligence Platform

**Scan. Verify. Understand.**

| | |
| --- | --- |
| Hackathon | Smart India Hackathon **2026** |
| Problem statement | **26034** |
| Problem | Software system to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels |
| Organization | Ministry of Consumer Affairs, Food & Public Distribution |
| Department | Department of Consumer Affairs |

LabelGuard AI is an **AI-assisted decision-support and inspection tool**. It is not a Legal Metrology officer and does **not** make a final legal determination.

---

## Problem

Packaged commodities sold in India must carry required declarations under the Legal Metrology (Packaged Commodities) Rules, 2011 — including identity of manufacturer/packer/importer, net quantity, retail sale price (MRP), applicable date information, and consumer-care contact.

Manual inspection is slow: an officer or consumer must read small print, compare it with the applicable rule version, and record evidence. Scale is hard — many SKUs, many languages, poor lighting, and rules that change over time. Missing a declaration and failing to *read* a declaration are easy to confuse, which can produce false conclusions.

---

## Solution

LabelGuard AI is an **AI-assisted Legal Metrology inspection platform** for Indian packaged commodities.

**Primary USP:** Legal Metrology compliance intelligence — not nutrition scanning, not a chatbot, not a generic product scanner.

**Secondary value (planned):** nutrition and ingredient information to help consumers understand a label.

Intended path: capture a label, extract structured declarations, run a **deterministic rule engine**, and produce an automated assessment with evidence references and a recommendation for manual verification when needed.

---

## Primary USP

```text
Product label
      ↓
Image processing          (planned)
      ↓
OCR                       (planned)
      ↓
Information extraction    (planned)
      ↓
Legal Metrology rule engine   ← implemented
      ↓
Compliance assessment         ← implemented
      ↓
Evidence                      (schema + mock UI)
      ↓
Report                        (schema only)
```

The Legal Metrology engine is **rule-based and deterministic**. An LLM is **not** the final legal authority. AI (when added) may detect, read, extract, and explain. The engine decides `COMPLIANT` / `POTENTIAL_NON_COMPLIANCE` / `MANUAL_REVIEW` from structured declarations and stored rules.

---

## Target users

### Enforcement officials

Inspect packaged commodities, check applicable Legal Metrology requirements for the inspection date and product category, and record potential issues with rule references. Evidence images and PDF reports are **planned**; the engine already returns explainable assessment items.

### Consumers

Understand what a label is declaring and, later, view nutrition and ingredient information. Those intelligence modules are **not implemented**. The mobile app currently shows a mock inspection experience.

---

## Key features

| Feature | Purpose | Status |
| --- | --- | --- |
| FastAPI health API | Process liveness | **Implemented** |
| PostgreSQL schema | Persist users, products, inspections, rules, findings | **Implemented** (schema; no CRUD API yet) |
| Legal Metrology rule engine | Deterministic assessment of structured declarations | **Implemented** |
| Rule versioning & applicability | Select the in-force, category-matching rule version | **Implemented** |
| Deterministic validators | MRP, net quantity, dates, required declarations, consumer care | **Implemented** |
| Confidence on declarations / validator results | Per-field and per-check scores; no overall “% legal” score | **Implemented** in engine contracts |
| Mobile UI (Expo) | Home, scan placeholder, processing, evidence, history, profile | **Implemented** (mock data) |
| UI multilingual support | en, hi, mr, bn, ta, gu, te | **Implemented** (UI only) |
| Inspection history | Store and list inspections | **Partial** (DB table + mock History screen; no API) |
| Evidence | Bounding boxes, rule refs, highlighted images | **Partial** (schema + mock screen; no image generator) |
| Image quality analysis | Blur / glare / recapture | **Not implemented** |
| OpenCV preprocessing | Deskew, enhance | **Not implemented** |
| PaddleOCR | Read label text | **Not implemented** |
| Declaration extraction | OCR text → structured fields | **Not implemented** (contract only) |
| Nutrition intelligence | Parse nutrition table | **Not implemented** (schema + Coming Soon UI) |
| Ingredient intelligence | Parse ingredient list | **Not implemented** (schema + Coming Soon UI) |
| PDF reports | Inspection PDF | **Not implemented** (schema only) |
| Camera / live scan | Capture from phone | **Not implemented** |
| Mobile ↔ API | Real inspections from the app | **Not implemented** |
| Authentication | Login, roles | **Not implemented** |
| Barcode / QR | Product identity | **Not implemented** |
| E-commerce analysis | URL → compliance | **Not implemented** |

---

## Architecture

**Target architecture** (not all boxes exist as running code):

```text
                    MOBILE APP
               React Native + Expo
                         │
                         ▼
                    FASTAPI API
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       OpenCV        PaddleOCR      PostgreSQL
          │              │
          └───────┬──────┘
                  ▼
          INFORMATION EXTRACTION
                  │
          ┌───────┴────────┐
          ▼                ▼
   LEGAL METROLOGY     NUTRITION
       ENGINE            ENGINE
          │                │
          └───────┬────────┘
                  ▼
             RESULT ENGINE
                  │
          ┌───────┼────────┐
          ▼       ▼        ▼
        Legal  Nutrition Evidence
          │
          ▼
       PDF REPORT
```

**Current repository state:** Expo mobile (mock) and FastAPI (`/health` only) plus a PostgreSQL schema. The Legal Metrology engine runs **in-process** (callable from Python tests and future services). OpenCV, PaddleOCR, extraction, nutrition engine, and PDF generation are **not** in this repo.

---

## Legal Metrology compliance

The engine receives inspection date, product category, product context, and structured declarations. It resolves **which rule versions apply**, runs registered validators, and aggregates an **automated assessment**.

| Status | Meaning |
| --- | --- |
| `COMPLIANT` | Applicable verified checks passed; not a legal certificate |
| `POTENTIAL_NON_COMPLIANCE` | Strong evidence that a requirement appears unsatisfied |
| `MANUAL_REVIEW` | Uncertain, unverified rule, missing validator, or no applicable rules |

**Missing vs unread**

- *Information is missing* — only when evidence of absence is reliable (for example a readable label and a confident “not on the pack” signal).
- *Information could not be reliably detected* — e.g. OCR `NOT_DETECTED` at low confidence → **`MANUAL_REVIEW`**, not a violation.

`NOT_DETECTED` is **not** the same as legally missing. Prototype rules come from official 2011 India Code text (selected clauses). Country-of-origin is stored as an **unverified draft** and cannot create an authoritative violation.

Official sources: [Department of Consumer Affairs — Legal Metrology](https://consumeraffairs.gov.in/pages/legal-metrology-act).

---

## AI / computer vision

**Not implemented in this repository.** There is no OpenCV or PaddleOCR dependency and no image pipeline.

What exists today:

- Contract `OCRResult`: `text`, `confidence` in `[0, 1]`, pixel `bbox` `[x1, y1, x2, y2]`
- Contract `ImageQualityResult`: `usable`, optional `reason`
- Validators consume **already structured** `Declaration` objects (including optional bbox and confidence)

---

## Nutrition & ingredient intelligence

These are **secondary** features. They are not the product’s primary purpose.

- Schemas and database tables exist so legal analysis can proceed when nutrition/ingredients are absent.
- No nutrition or ingredient engine is implemented.
- Mobile Home tiles open a Coming Soon screen.
- The project does not diagnose medical conditions or call a product “dangerous” from ingredient text.

---

## Evidence

Intended: original image, annotated crop, bounding box, detected text, confidence, rule reference, recommended action.

**Today:** validators attach declaration bbox/source/confidence to each result; the `evidence` table and `EvidenceItem` schema exist; the mobile Evidence screen is **mock**. Highlighted-image generation is **not** implemented.

---

## Reports

PDF generation is **not implemented**. A `reports` table and `ReportResult` contract exist so a future generator can mark `PENDING` / `READY` / `FAILED` without discarding the inspection.

---

## Technology stack

| Layer | Technology | In this repo |
| --- | --- | --- |
| Mobile | React Native, Expo SDK 54, TypeScript | Yes |
| API | Python 3.13+, FastAPI, Uvicorn, Pydantic | Yes |
| Data | PostgreSQL, SQLAlchemy 2, Alembic, psycopg | Yes (schema; DB optional for `/health`) |
| Legal core | Pure Python + Pydantic (no LLM) | Yes |
| Tests | pytest, pytest-cov, httpx | Yes (`backend/tests`) |
| OpenCV | — | **Planned** (not installed) |
| PaddleOCR | — | **Planned** (not installed) |
| ReportLab / PDF | — | **Planned** (not installed) |
| NativeWind | — | Not used (StyleSheet + theme tokens) |

---

## Project structure

```text
labelguard/
├── backend/
│   ├── app/                 # FastAPI, schemas, database, compliance engine
│   ├── migrations/          # Alembic (head: 0003_legal_rule_traceability)
│   ├── seeds/               # legal rule seed
│   ├── tests/               # pytest (legal core + API health)
│   ├── requirements.txt
│   └── .env.example
├── mobile/                  # Expo 54 app (mock inspections)
├── legal-rules/
│   └── 2011/rules.json      # prototype 2011 clauses
├── docs/
│   └── PROJECT_CONTEXT.md   # full technical context
└── README.md
```

There is no repository-root `tests/` directory; backend tests live under `backend/tests/`.

---

## Local development

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`/health` does **not** require PostgreSQL. Copy `backend/.env.example` to `backend/.env` and edit locally. Never commit `.env`.

Optional database (migrations and seed):

```powershell
alembic upgrade head
python -m seeds.legal_rules
```

### Mobile

```powershell
cd mobile
npm install
npx expo start --lan
```

Use **Expo Go matching SDK 54**. Phone and PC must be on the same Wi-Fi.

### Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

Persistence tests skip if PostgreSQL is not running.

---

## API

Only these routes exist:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness (`{"status":"ok"}`) |
| `GET` | `/api/v1/health` | Same, versioned |

OpenAPI (when the server is running): http://127.0.0.1:8000/docs

There is no scan, inspection, or auth endpoint yet. `ScanResponse` is a **future** contract, not a live route.

Errors use `{ "error": { "code", "message", "details" } }`.

---

## Testing

Backend tests live in `backend/tests/` (health, errors, logging, schemas, models, rule storage, applicability, validators, engine, pipeline/edge cases). They are designed to run **without OCR** and **without PostgreSQL** except for skipped persistence tests.

This README does not claim a current pass/fail count. Run `pytest` locally to verify.

The mobile app has no automated test suite in-repo.

---

## Security

| Topic | Status |
| --- | --- |
| `.env` gitignored; `.env.example` committed | Yes |
| `DATABASE_URL` treated as a secret; log redaction for tokens/passwords | Yes |
| Pydantic validation on declarations (confidence 0..1; no `MISSING` status) | Yes |
| Stack traces not returned to API clients | Yes |
| CORS | Off unless `CORS_ORIGINS` is set |
| Authentication / authorization | **Not implemented** |
| Upload / file validation | **Not implemented** (no upload API) |

---

## Development roadmap

This is the **product** sequence. Backend work already delivered a deterministic rule engine (see `docs/PROJECT_CONTEXT.md` for the internal backend phase list).

| Phase | Scope | Status in this repo |
| --- | --- | --- |
| 1 — Foundation | Repo, mobile shell, API process | **Done** (health API + Expo mock UI) |
| 2 — Backend | FastAPI, errors, logging, contracts | **Done** |
| 3 — PostgreSQL | Schema + Alembic | **Done** (optional at runtime) |
| 4 — Legal rule engine | Storage, versioning, validators, assessment | **Done** |
| 5 — Image processing | OpenCV quality / preprocess | **Not started** |
| 6 — OCR | PaddleOCR | **Not started** |
| 7 — Declaration extraction | OCR → structured fields | **Not started** (schema only) |
| 8 — OCR → compliance integration | Scan API wiring | **Not started** |
| 9 — Evidence | Highlighted images | **Partial** (schema + mock UI) |
| 10 — Nutrition | Nutrition engine | **Not started** |
| 11 — Ingredients | Ingredient engine | **Not started** |
| 12 — Mobile integration | Live API + camera | **Not started** |
| 13 — Inspection history | List/get inspections API | **Partial** (table + mock list) |
| 14 — PDF reports | Generate PDFs | **Not started** |
| 15 — Advanced features | Barcode, fingerprint, e-commerce, etc. | **Not started** |

---

## Team development

```text
main
  → feature branch
  → development + tests
  → pull request
  → review
  → merge
```

Example branches: `feature/ocr`, `feature/nutrition`, `feature/evidence`.

Do **not** develop directly on `main`. Teammate modules should integrate through the Pydantic contracts in `backend/app/schemas/` and must not rewrite the legal engine.

---

## Engineering principles

- The rule engine is deterministic.
- An LLM is not the legal authority.
- OCR uncertainty ≠ missing declaration.
- Preserve OCR bounding boxes and confidence scores.
- Do not invent extracted values.
- Do not claim exact physical millimetres without calibration.
- Prefer manual review when confidence is low.
- Keep legal rules separate from application logic (`legal-rules/` + `legal_rules` table).
- Keep modules loosely coupled (OCR ≠ compliance ≠ nutrition).
- Do not hard-code secrets.
- Do not silently modify unrelated files.

---

## Limitations

- No camera, no OCR, no scan API — the engine is tested with **manual declaration fixtures**.
- Mobile inspections are **mock**; they are not loaded from FastAPI.
- Seed rules are a **small prototype** of 2011 clauses, not the full Rules plus every amendment.
- Country-of-origin is an unverified draft row.
- Rule 6(1)(f) (size) has no validator yet.
- No authentication, PDF, nutrition engine, or ingredient engine.
- No overall “percent compliant” score (`assessment_confidence` is unused / null by design).

---

## Future scope

Planned or possible later (not in the current codebase):

- Calibrated print-size measurement
- Barcode / QR product identity
- More Indian languages for **label** understanding (UI already has seven locales)
- E-commerce URL analysis
- Offline mode
- Product fingerprinting (“previously inspected”)
- Inspector dashboards
- Optional local LLM for explanation only (never for the legal verdict)
- Advanced computer vision (glare, blur, recapture)

---

## SIH relevance

Problem Statement **26034** asks for a system that checks packaged-commodity compliance under the 2011 Rules by scanning products, images, and labels.

This repository already provides the **deterministic Legal Metrology core** (versioned rules, applicability, validators, assessment statuses) plus a **mobile inspection UI prototype** and a **PostgreSQL schema**. Image capture, OCR, and end-to-end scan integration remain the next product phases so the official workflow can run from a photograph to an explainable automated assessment.

---

## Disclaimer

LabelGuard AI is an AI-assisted decision-support and inspection tool. It is not a replacement for an authorized Legal Metrology officer and does not itself make a final legal determination.

AI and engine outputs should be treated as **automated assessments** that require appropriate human verification.

---

## License

License: To be determined.

(`mobile/LICENSE` is the Expo scaffold copyright, not a project-wide LabelGuard license.)
