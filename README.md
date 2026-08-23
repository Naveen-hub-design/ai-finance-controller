# AI Finance Controller

A secure, scalable financial control platform for B2B merchants. Planned
capabilities: **AI anomaly and fraud detection**, **conversational financial
auditing (RAG)**, **automated ledger reconciliation**, and an **AI Finance
Controller** that coordinates them.

> **Status: M01 — Foundation.** This repository currently contains only the
> production-oriented infrastructure (API skeleton, database, broker, worker,
> frontend shell, reverse proxy). No business or AI features are implemented.

## Technology stack

| Layer      | Technology                                        |
| ---------- | ------------------------------------------------- |
| API        | Python 3.12, Flask, Gunicorn, SQLAlchemy          |
| Database   | PostgreSQL 16 (`pgvector` image), pgvector, pgcrypto |
| Broker     | Redis 7                                           |
| Async      | Celery 5 (dedicated `worker` service)             |
| Frontend   | React 19, Vite 6, TypeScript                      |
| Entry point| Nginx (reverse proxy)                             |
| Packaging  | Docker Compose                                    |

## Quick start

Requires only Docker (with Compose v2) — no host Python or Node needed.

```bash
cp .env.example .env       # then edit values; never commit .env
docker compose up --build
```

- Frontend: <http://localhost>
- API health: <http://localhost/api/health>

All browser traffic goes through Nginx (`/` → frontend, `/api/*` → Flask).

## Health check

```bash
curl http://localhost/api/health
```

```json
{
  "status": "healthy",
  "service": "finance-controller-api"
}
```

## High-level architecture

```text
Browser ──► nginx ──┬── /       ► frontend (React static build)
                    └── /api/*  ► api (Flask/Gunicorn)
                                     ├─ postgres 16 + pgvector (datastore)
                                     └─ redis 7 (broker/backend)
                                          ▲
                          worker (Celery)─┘
```

See [docs/architecture/system-overview.md](docs/architecture/system-overview.md)
for details.

## Repository layout

```text
backend/    Flask app factory, health endpoint, tests
frontend/   React + Vite + TypeScript shell
worker/     Celery app foundation (no business tasks yet)
database/   Postgres image with init SQL (extensions), seeds placeholder
nginx/      Reverse proxy configuration
docs/       architecture/, decisions/, demo/
scripts/    helper scripts (bootstrap)
tests/      cross-service smoke tests (shell)
```

## Testing

Backend unit/integration tests:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Cross-service smoke checks against a running stack:

```bash
bash tests/smoke_test.sh
```

## Project rules

- All secrets come from environment variables (`.env`, git-ignored). The
  committed `.env.example` contains placeholders only.
- **Financial calculations must never depend on LLM-generated arithmetic**
  ([ADR 004](docs/decisions/004-financial-precision.md)). Future monetary code
  uses Python `Decimal` and PostgreSQL `NUMERIC`.

## Planned (not yet implemented)

Authentication/JWT/RBAC · merchant management · transactions, invoices,
vendors · ledger & reconciliation · OCR ingestion · embeddings/pgvector usage ·
RAG auditing · anomaly/fraud detection (Isolation Forest) · LLM integration &
AI agent · dashboards (Tailwind/shadcn/Recharts) · WebSockets · cloud
deployment.

Each will be introduced in its own milestone.
