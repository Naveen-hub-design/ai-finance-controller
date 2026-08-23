# System Overview — AI Finance Controller

## What it is

A secure, scalable financial control platform for B2B merchants. Planned
capabilities: AI anomaly/fraud detection, conversational financial auditing
(RAG), automated ledger reconciliation, and an AI Finance Controller agent
that coordinates them.

M01 delivers **infrastructure only**: no business or AI features.

## Current topology (M01)

```text
                ┌──────────────────────────── Docker network ────────────────────────────┐
                │                                                                        │
 Browser ──► nginx :80 ──┬── /          ► frontend (React build served by nginx:alpine) │
                │         └── /api/*     ► api (Flask + Gunicorn, 0.0.0.0:5000)         │
                │                                            │                          │
                │                                            ├──► postgres (pgvector/pg16)│
                │                                            └──► redis (broker/cache)    │
                │                                                ▲                        │
                │                                    worker (Celery)                       │
                └────────────────────────────────────────────────────────────────────────┘
```

| Service    | Image / build              | Role                                        |
| ---------- | -------------------------- | ------------------------------------------- |
| `nginx`    | `nginx:alpine` + config    | Public entry point, reverse proxy           |
| `frontend` | Node 22 build → nginx:alpine | Static React/Vite bundle                  |
| `api`      | Python 3.12-slim + Gunicorn | Flask REST API (application factory)       |
| `worker`   | Python 3.12-slim + Celery  | Async task execution (no tasks yet)         |
| `postgres` | `pgvector/pgvector:pg16`   | Primary datastore, pgvector + pgcrypto      |
| `redis`    | `redis:7-alpine`           | Celery broker/result backend                |

## Key design points

- The browser only talks to **nginx**; Flask and the frontend bundle are
  internal services.
- The API is built with a Flask **application factory**
  (`backend/app/__init__.py`), keeping configuration testable and modules small.
- PostgreSQL runs on the pgvector-enabled image so vector columns will be
  available to later RAG milestones without a migration of the database engine.
- Celery is wired to Redis but defines no business tasks yet.
- Financial precision rule: see
  [decisions/004-financial-precision.md](../decisions/004-financial-precision.md).

## Planned evolution (not implemented)

- Authentication, JWT, RBAC → later milestone
- Merchant/transaction/invoice/ledger schema → later milestone
- OCR, embeddings, RAG pipeline, reconciliation, anomaly detection → later
  milestones, executed primarily in the `worker` service
- Tailwind/shadcn UI system and dashboards → later milestone
