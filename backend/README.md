# LabelGuard AI — Backend

AI-assisted Legal Metrology compliance API for SIH 2026 (Problem Statement 26034).

This folder is the **core backend**. Teammate modules (OCR, nutrition, evidence, reports) plug in through interfaces in later phases. They must not change this application’s legal engine or API contracts.

## Current phase

**Phase 10 — Testing and hardening**

The Legal Metrology core is covered by fixture-based unit, integration, and domain tests. Overlapping rule versions are refused instead of silently chosen. See `docs/compliance-testing.md`.

## Current phase notes (Phase 2 still applies)

The process still answers `/health`. Failures now return a single envelope:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": {}
  }
}
```

Each request is logged with method, path, status, duration and a request id. Query strings, bodies, and secrets are not logged. Stack traces stay in server logs only.

## Requirements

- Python 3.13 or later
- PostgreSQL 16+ when you want to run migrations (the API process starts without it)
- A virtual environment under `backend/.venv` (already created on this machine)

## Setup

From the `backend/` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, activate with `source .venv/bin/activate` and copy the env file with `cp .env.example .env`.

`.env` is git-ignored. Edit it locally; do not commit it.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or:

```powershell
python -m app.main
```

OpenAPI docs: http://127.0.0.1:8000/docs

## Health checks

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
```

Expected body for both:

```json
{"status":"ok"}
```

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

Expected: previous tests plus Phase 10 pipeline, edge-case, and input-safety tests. Persistence tests skip if PostgreSQL is not running.

## Migrations

`/health` does not require PostgreSQL. Applying revisions does.

```powershell
alembic upgrade head
alembic current
```

Expected `alembic current` after a successful upgrade:

```text
0003_legal_rule_traceability (head)
```

Then seed the prototype rules (safe to run twice):

```powershell
python -m seeds.legal_rules
```

## Contracts

| Module | Schema | Notes |
| --- | --- | --- |
| OCR teammate | `OCRResult` | `bbox` is `[x1, y1, x2, y2]` pixels |
| Extraction → engine | `Declaration` | Status is never `MISSING` |
| Legal engine | `ComplianceResult` | Snake_case; not a legal verdict |
| One validator | `ValidationResult` | `PASS` is not inspection `COMPLIANT` |
| Compliance engine | `ComplianceAssessment` | Automated assessment; `assessment_confidence` is null |
| Mobile app | `InspectionResponse` | CamelCase aliases matching `mobile/types/inspection.ts` |
| Nutrition teammate | `NutritionResult` | `null` is valid |
| Evidence / reports | `EvidenceItem`, `ReportResult` | Failure is a status, not a lost inspection |

## What this phase does not include

Scan orchestration, OCR, authentication, evidence images, PDF, and live mobile integration. Those arrive in later numbered phases.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_NAME` | Title in OpenAPI docs | `LabelGuard AI` |
| `APP_ENV` | `development`, `staging`, or `production` | `development` |
| `HOST` | Bind address | `127.0.0.1` |
| `PORT` | Bind port | `8000` |
| `CORS_ORIGINS` | Comma-separated browser origins | empty (no CORS headers) |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` | `INFO` |
| `DATABASE_URL` | PostgreSQL DSN (stored as a secret; never logged) | `postgresql+psycopg://postgres:postgres@127.0.0.1:5432/labelguard` |
