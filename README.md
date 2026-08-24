# LabelGuard AI

## AI-Powered Legal Metrology Compliance & Product Label Intelligence Platform

**Scan. Verify. Understand.**

A **consumer-first** AI-assisted platform that reads packaged-product labels, evaluates applicable Legal Metrology requirements, and (as the product direction) verifies label claims against **current** observable or measured evidence.

| | |
| --- | --- |
| Hackathon | Smart India Hackathon **2026** |
| Problem statement | **26034** |
| Problem | Software system to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels |
| Organization | Ministry of Consumer Affairs, Food & Public Distribution |
| Department | Department of Consumer Affairs |

LabelGuard is **not** a food scanner, calorie tracker, or chatbot. It is **not** a government authority.

---

## Problem

Packaged commodities in India must carry required declarations under the Legal Metrology (Packaged Commodities) Rules, 2011 — manufacturer/packer/importer identity, net quantity, MRP, applicable dates, consumer-care contact, and others.

For a **consumer**, the label is hard to use in real life: small print, mixed languages, and no easy way to check whether what the pack *says* matches what you can see or measure *now* (for example a declared 500 g vs a scale reading). For scale, the same checks are slow to do by hand and easy to get wrong — especially mixing up “the camera could not read it” with “it is not on the pack.”

---

## Solution

LabelGuard AI is a **consumer-first AI-assisted product label intelligence and Legal Metrology verification platform**.

**Primary USP:** Legal Metrology **plus** label-to-product verification (declared claim vs current observation). Nutrition and ingredient intelligence are **secondary** consumer features.

The product should help a consumer:

1. Scan a packaged product  
2. Read and understand the label  
3. Extract important declarations  
4. Check applicable Legal Metrology requirements  
5. Compare label claims with a **current** observation or measurement  
6. Surface potential discrepancies with evidence and confidence  
7. Explain what was detected — without saying “the product is illegal”  
8. Compare nutrition across several scanned products (**planned**)  
9. Save evidence and reports (**planned**)

Enforcement-style workflows can still sit on the same architecture. They are **not** the centre of the current product story.

---

## Primary USP

```text
SCAN PRODUCT
      ↓
CAPTURE IMAGE                 (planned)
      ↓
IMAGE QUALITY / PROCESSING    (planned)
      ↓
OCR                           (planned)
      ↓
DECLARATION EXTRACTION        (planned)
      ↓
LEGAL METROLOGY CHECK         ← engine implemented
      ↓
LABEL-TO-PRODUCT VERIFICATION (planned — next product direction)
      ↓
RESULT AGGREGATION            ← engine implemented for legal checks
      ↓
EVIDENCE / EXPLANATION        (partial)
      ↓
NUTRITION / INGREDIENTS       (planned)
      ↓
REPORT / HISTORY              (partial)
```

Legal Metrology is **deterministic and rule-based**. An LLM is **never** the final legal authority:

```text
OCR / AI  →  structured information  →  deterministic rule engine  →  assessment
```

---

## Label-to-product verification (product direction)

**Status: not implemented.** This is the next major consumer capability after the existing legal core. It is **not** a comparison with an older product version or a historical database.

The **label** is the expected claim. The **current** product image, user measurement, or other observation is what is checked.

```text
LABEL / TEXT  →  OCR + extraction  →  EXPECTED CLAIMS
CURRENT PRODUCT / MEASUREMENT      →  OBSERVATION
        ↓
EXPECTED + OBSERVED  →  VERIFICATION  →  MATCH / POTENTIAL MISMATCH / UNVERIFIED
```

**Example (quantity):** label `500 g`, consumer scale `472 g` → “Potential quantity discrepancy detected.” Not “fraud,” “the company cheated,” or “illegal.” Any legal assessment must still use stored rules and **permissible tolerances** when those are encoded from official sources. The camera must **not** be described as a weighing scale. Physical mass comes from a user-provided (or otherwise reliable) measurement. Physical dimensions need calibration.

Possible check types (architecture, not current code): quantity, count, visible text/value (e.g. MRP), product identity, other observable consistency checks.

A result should eventually show **declared value**, **observed value**, **difference**, **applicable rule**, **confidence**, and **verification status**.

---

## Target users

### Consumers (primary)

Scan a pack, understand the label, see Legal Metrology checks in plain language, optionally verify a claim against a current measurement, keep evidence, and later compare nutrition. The live app today is a **mock** Expo UI (no camera, no API).

### Enforcement officials (supported by architecture, not the UI centre)

The same deterministic engine can serve inspection. The `users` table still has an `INSPECTOR` role default; authentication is **not** implemented. The README and product experience are **consumer-first**, not an inspector dashboard.

---

## Consumer experience (intended)

```text
HOME → SCAN → PRODUCT OVERVIEW → LEGAL / LABEL CHECK
  → LABEL-TO-PRODUCT VERIFICATION → WHAT WAS DETECTED?
  → NUTRITION → INGREDIENTS → COMPARE → EVIDENCE → REPORT / SAVE
```

**Current mobile screens:** Home, Scan (placeholder), Processing (simulated), Evidence (mock), History (mock), Profile, Language, Coming Soon. There is no product-overview, verification, compare, or report flow yet.

Conceptual result (not the current engine JSON):

- Legal label status: Compliant / Potential Non-Compliance / Manual Review / Could Not Verify  
- Label-to-product status: Potential Mismatch (**planned**; not an engine enum today)  
- Declared vs observed, rule reference, recommendation: manual verification  

The **implemented** engine statuses remain: `COMPLIANT`, `POTENTIAL_NON_COMPLIANCE`, `MANUAL_REVIEW`. Do not treat “Potential Mismatch” or “Could Not Verify” as live API values.

---

## Key features

| Feature | Purpose | Status |
| --- | --- | --- |
| FastAPI health API | Process liveness | **Implemented** |
| PostgreSQL schema | Persist products, inspections, rules, findings | **Implemented** (schema; no CRUD API) |
| Legal Metrology rule engine | Deterministic check of structured declarations | **Implemented** |
| Rule versioning & applicability | In-force version for date + category | **Implemented** |
| Deterministic validators | MRP, net quantity, dates, required fields, consumer care | **Implemented** |
| Per-check confidence | Declaration / validator scores; no overall “% legal” | **Implemented** in contracts |
| Consumer mobile UI | Home, scan placeholder, history, language | **Implemented** (mock data) |
| UI languages | en, hi, mr, bn, ta, gu, te | **Implemented** (UI only) |
| Evidence | Photos, boxes, rule refs, measurements | **Partial** (schema + mock screen) |
| Inspection history | Save / list scans | **Partial** (table + mock list) |
| Label-to-product verification | Declared vs current observation | **Not implemented** |
| Multi-product nutrition compare | Rank by user-selected nutrients | **Not implemented** |
| Image quality / OpenCV | Recapture, preprocess | **Not implemented** |
| PaddleOCR | Read the label | **Not implemented** |
| Declaration extraction | OCR → structured fields | **Not implemented** |
| Nutrition / ingredient engines | Parse panel and ingredients | **Not implemented** (schema + Coming Soon) |
| Camera / scan API | Live capture → backend | **Not implemented** |
| PDF reports | Consumer-facing report | **Not implemented** |
| Auth, barcode/QR, e-commerce | — | **Not implemented** |

---

## Architecture

**Target** (not all boxes exist):

```text
                 MOBILE APP
            React Native + Expo
                      │
                      ▼
                FASTAPI BACKEND
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
    OpenCV        PaddleOCR       PostgreSQL
       │              │
       └───────┬──────┘
               ▼
       INFORMATION EXTRACTION
               │
       ┌───────┴────────┐
       ▼                ▼
LEGAL METROLOGY    NUTRITION ENGINE
    ENGINE                │
       │                  │
       └────────┬─────────┘
                ▼
      LABEL-TO-PRODUCT
       VERIFICATION
                │
                ▼
        RESULT AGGREGATOR
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
   Compliance Verification Evidence
      │
      ▼
    Reports
```

**In the repo today:** Expo mock app; FastAPI `/health` only; PostgreSQL schema; in-process Legal Metrology engine. No OpenCV, PaddleOCR, extraction service, verification engine, nutrition engine, or PDF.

---

## Legal Metrology

Primary USP. The implemented engine takes inspection date, category, context, and structured declarations; selects applicable **verified** rule versions; runs validators; aggregates an automated assessment.

Prototype declarations in seed data include manufacturer identity, generic name, net quantity, date (where applicable), MRP, size-when-relevant, consumer-care contact. Country of origin is a **draft / unverified** row and cannot create an authoritative violation.

| Implemented status | Meaning |
| --- | --- |
| `COMPLIANT` | Applicable verified checks passed — not a legal certificate |
| `POTENTIAL_NON_COMPLIANCE` | Strong evidence a requirement appears unsatisfied |
| `MANUAL_REVIEW` | Uncertain, unverified rule, missing validator, or nothing applicable |

Product language may also use **Potential Mismatch** (label vs observation) and **Could Not Verify** (insufficient evidence). Those are **not** engine enums yet.

Always distinguish:

- **Missing** — reliable evidence of absence  
- **Could not detect** — e.g. blurry OCR (`NOT_DETECTED` + low confidence → review, not a violation)  
- **Potential mismatch** — declared vs observed (**planned**)

Official source: [Department of Consumer Affairs — Legal Metrology](https://consumeraffairs.gov.in/pages/legal-metrology-act).

---

## Nutrition comparison (planned)

**Not implemented.** A future consumer feature: scan several products and compare calories, sugar, added sugar (if present), protein, carbs, fat, saturated fat, trans fat, fibre, sodium. The user picks priorities (lower sugar, higher protein, …). The system ranks **by those parameters** and explains why.

It must **not** say “this product is healthiest.” Example: “Product B ranks highest based on your selected parameters” with checks and caveats. No medical claims.

---

## Evidence and reports

**Intended (consumer-facing):** product photo, label photo, highlighted region, measurement evidence, optional purchase proof, notes, timestamp, declared vs observed, rule reference, confidence. Not a fake government grievance portal; any later guidance should point to **official** channels.

**Today:** validators keep bbox/source/confidence; `evidence` / `reports` tables and schemas exist; mobile Evidence is mock. No image generator, no PDF, no measurement-evidence capture.

---

## Technology stack

| Layer | Technology | In this repo |
| --- | --- | --- |
| Mobile | React Native, Expo 54, TypeScript | Yes |
| API | Python 3.13+, FastAPI, Pydantic | Yes |
| Data | PostgreSQL, SQLAlchemy 2, Alembic | Yes (schema; optional for `/health`) |
| Legal core | Python (no LLM) | Yes |
| Tests | pytest, pytest-cov, httpx | Yes |
| OpenCV / PaddleOCR / ReportLab / Ollama | — | **Planned** (not installed) |

---

## Project structure

```text
labelguard/
├── backend/                 # FastAPI, schemas, DB, compliance engine, tests
├── mobile/                  # Expo 54 mock consumer UI
├── legal-rules/
│   └── 2011/rules.json
├── docs/
│   └── PROJECT_CONTEXT.md
└── README.md
```

Tests live in `backend/tests/`, not a root `tests/` folder.

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

PostgreSQL is **not** required for `/health`. Never commit `.env`.

```powershell
alembic upgrade head
python -m seeds.legal_rules
pytest
```

Persistence tests skip if Postgres is down.

### Mobile

```powershell
cd mobile
npm install
npx expo start --lan
```

Expo Go **SDK 54**, same Wi-Fi as the PC.

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness `{"status":"ok"}` |
| `GET` | `/api/v1/health` | Same, versioned |

No scan, verification, or nutrition endpoints. Docs: http://127.0.0.1:8000/docs

---

## Testing

`backend/tests/` covers health, schemas, rule storage, applicability, validators, engine, and pipeline edge cases **without OCR**. This README does not claim a pass count — run `pytest`. No mobile test suite.

---

## Security

`.env` gitignored; `DATABASE_URL` treated as a secret; log redaction; Pydantic validation; no stack traces to clients. CORS off unless `CORS_ORIGINS` is set. **No** auth, **no** upload/file validation (no upload API).

---

## Roadmap

**Already in the repo:** foundation, FastAPI, PostgreSQL schema, deterministic Legal Metrology engine (versioning, validators, assessment), mock consumer mobile UI.

**Next (not implemented):**

1. Label-to-product verification (declared vs current observation/measurement)  
2. Evidence-backed consumer verification (photos, measurements, notes)  
3. Multi-product nutrition comparison  
4. Consumer history and reports  
5. Then: camera + OCR integration, barcode/QR, more label languages, calibrated measurement, e-commerce analysis, offline support  

Do not treat this list as shipped software.

---

## Team development

```text
main → feature branch → tests → pull request → review → merge
```

Examples: `feature/ocr`, `feature/nutrition`, `feature/evidence`. Do not develop on `main`. Integrate through `backend/app/schemas/`; do not rewrite the legal engine.

---

## Engineering principles

- Rule engine is deterministic; LLM is not the legal authority.  
- OCR uncertainty ≠ missing declaration ≠ potential mismatch.  
- Preserve bounding boxes and confidence; never invent extracted values.  
- No exact millimetres or mass from an uncalibrated camera.  
- Prefer manual review when confidence is low.  
- Keep legal rules separate from app logic; keep modules loosely coupled.  
- No hardcoded secrets; no silent unrelated file changes.  
- No medical claims; no “fraud” language from automated output.

---

## Limitations

- No camera, OCR, scan API, or verification engine — legal tests use **manual declaration fixtures**.  
- Mobile data is **mock**.  
- Seed rules are a **prototype** 2011 set, not every amendment.  
- Size rule has no validator; origin rule is unverified draft.  
- No nutrition compare, PDF, or authentication.  
- Engine has no overall legal-confidence percentage (`assessment_confidence` stays unset).

---

## Future scope

Calibrated measurement, barcode/QR, more Indian languages for **label** OCR, e-commerce analysis, offline mode, product fingerprinting, dashboards, optional local LLM **for explanation only**, advanced vision. All **future**.

---

## SIH relevance

Problem **26034** asks for a system that checks packaged-commodity compliance under the 2011 Rules by scanning products, images, and labels.

LabelGuard AI is a **consumer-first** AI-assisted platform that reads packaged-product labels, evaluates applicable Legal Metrology requirements, is designed to verify label claims against **current** observable or measurement evidence, highlights potential discrepancies, and will provide understandable nutrition and ingredient intelligence.

This repository already has the **deterministic legal core** and a **consumer UI prototype**. Capture, OCR, label-to-product verification, and comparison are the next product steps.

---

## Disclaimer

LabelGuard AI is an AI-assisted decision-support and product-label verification tool. It is not a replacement for an authorized Legal Metrology officer and does not itself make a final legal determination.

Findings are **automated assessments**. They require appropriate human verification. LabelGuard is not a government complaints portal.

---

## License

License: To be determined.

(`mobile/LICENSE` is the Expo scaffold copyright, not a project-wide LabelGuard license.)
