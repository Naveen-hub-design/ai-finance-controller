# AI Finance Controller

A secure, enterprise-grade financial control and auditing platform designed for B2B merchants and financial teams. The platform features **multi-tenant business isolation**, **deterministic anomaly and risk detection**, **automated multi-bank ledger reconciliation** with human-in-the-loop exception workflows, and **conversational AI financial analysis**.

---

## Capabilities & Architecture

| Module | Description | Implementation Status |
| :--- | :--- | :--- |
| **Authentication & RBAC** | JWT-based auth with server-enforced roles (`PLATFORM_ADMIN`, `MERCHANT`, `FINANCE_MANAGER`) and strict business data isolation. | **Complete & Verified** |
| **Ledger & Transactions** | Full account management, income/expense/transfer categorization, transaction CRUD, and instant CSV export. | **Complete & Verified** |
| **Reconciliation Engine** | Multi-source bank statement vs ledger reconciliation with automated matching (80%+ match rate), exception categorization, per-line durable review states, and audit trails. | **Complete & Verified** |
| **Risk & Anomaly Detection** | Rule-based and pattern-based anomaly detection engine identifying velocity spikes, duplicate candidates, and threshold breaches. | **Complete & Verified** |
| **Financial Intelligence** | Deterministic financial facts computation (cash flow, income, expense distribution, budget utilization, goal tracking). | **Complete & Verified** |
| **AI Controller & Explanations** | Evidence-bounded financial explanations, goal feasibility scoring, and proposal-only AI assistant via OpenAI Responses API. | **Complete & Configurable** |
| **Audit Log Trail** | Append-only audit records tracking reconciliation runs, review decisions, and financial administrative mutations. | **Complete & Verified** |
| **Platform Administration** | Dedicated platform administrator portal (`/admin`) for user management, system metrics, and cross-platform oversight. | **Complete & Verified** |

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite 6, Tailwind CSS, Recharts, Lucide Icons |
| **Backend API** | Python 3.12, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Gunicorn |
| **Database** | PostgreSQL 16 (pgvector, pgcrypto) / SQLite (Local dev & test isolation) |
| **Broker & Async** | Redis 7 & Celery 5 (`worker` service) |
| **Reverse Proxy** | Nginx (alpine) |
| **Testing** | Pytest (700+ tests), TypeScript (`tsc --noEmit`) |

---

## Quick Start

### Option 1: Native Local Run (No Docker Required)

#### 1. Start the Flask Backend
```bash
cd backend
python wsgi.py
```
*API runs at `http://127.0.0.1:5000` (`http://127.0.0.1:5000/api/health`).*

#### 2. Start the Frontend
```bash
cd frontend
npm run dev
# or: npx vite preview --port 5173
```
*Frontend loads at `http://localhost:5173` with automatic API proxying.*

---

### Option 2: Docker Compose (Full Stack)

Requires Docker Desktop with Compose v2:
```bash
cp .env.example .env       # edit values as needed
docker compose up --build
```
- Frontend UI: `http://localhost`
- API Health: `http://localhost/api/health`

---

## Demo Accounts (Instant 1-Click Access)

The platform comes pre-seeded with **Demo Corp** (250+ transactions, 4 accounts, 12 categories, 6 budgets, and reconciliation test batches):

| Role | Email | Password | Default Scope |
| :--- | :--- | :--- | :--- |
| **Merchant (Owner)** | `merchant@demo.com` | `demo-password-123` | Full financial control & member management |
| **Finance Manager** | `finance@demo.com` | `demo-password-123` | Operational financials, reconciliation & auditing |
| **Platform Admin** | `admin@demo.com` | `demo-password-123` | Cross-platform metrics & user management |

---

## AI Configuration

To enable live OpenAI generation (e.g., natural language explanations and AI goal intelligence):
1. Set your OpenAI API key in `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-5.6-luna
   ```
2. When the key is not set, the platform operates in **Graceful Degradation Mode**: all deterministic financials, analytics, risk algorithms, and reconciliation features work 100%, and AI endpoints return explicit, honest `503` notifications rather than fabricated data.

---

## Running Tests

Run the complete test suite:
```bash
cd backend
pytest
```
Run frontend typecheck:
```bash
cd frontend
npm run build
```
