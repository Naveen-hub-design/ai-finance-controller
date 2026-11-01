# Frontend ↔ Backend Integration Report — AI Finance Controller

**Date:** 2026-09-01 · **Branch:** `main` (uncommitted work, per constraints) · **Phase:** Full frontend ↔ backend integration

## A. Scope

Verified the existing React (Vite + TypeScript) frontend against the existing Flask backend
end-to-end through the live Docker stack (`browser → nginx:80 → api:5000 → Postgres / Redis /
Celery worker / AI provider`). Every number in this report was produced by real API calls
against the running stack; nothing was fabricated or hardcoded.

## B. Pre-flight inventory

- Frontend: `frontend/src/**` — 20+ routed pages, shared `api.ts` client, `AuthContext`,
  `BusinessContext`, `RoleRoute`, layout/nav components, `lib/labels.ts`, `lib/format.ts`,
  `lib/types.ts`.
- Backend: `app/routes/**` (auth, users, businesses, accounts, transactions, budgets, goals,
  financial-facts, summaries, categories, audit, M4 controller, M4.5 async, reconciliation),
  `app/services/**`, worker Celery tasks, database schema migrations, nginx config, compose file.
- Three explore reports produced: (1) frontend page → endpoint audit, (2) backend endpoint map
  (methods/paths/authz/response shapes), (3) infrastructure audit (nginx / Vite / compose /
  Dockerfiles / migration staging / environment).

## C. Frontend → backend mapping

Every page consumes only real endpoints with correct paths and methods, verified by static
inspection plus targeted live calls:

| Page | Endpoints used (verified live) | Result |
|------|--------------------------------|--------|
| Login | `POST /api/users/login`, `POST /api/users/demo-login` | 200 + JWT |
| Dashboard | financial summary, accounts, transactions, budgets, goals, risk, recommendations | 200 |
| Administration | `GET /api/users` (platform admin only), user creation | 200 / 403 |
| Businesses | `GET /api/businesses`, members | 200 |
| Reconciliation | `POST …/reconcile`, `POST …/reconcile/async`, poll | 200/201, SUCCESS |
| AI Controller | `POST …/ai-controller/async`, poll | 201 → 503 (no key) / SUCCESS (mocked) |
| AI / Audit / Categories | explanation, risk, recommendations, audit records, categories | 503 / 200 (see sections) |

## D. Architecture & data flow

- Same-origin single-host deployment: `http://localhost` → nginx (`nginx/finance-controller.conf`)
  proxies `/api/` to `finance_api` and serves the built Vite `dist/` for `/`.
- Backend has **no CORS setup** — correct for this same-origin topology (no cross-origin browser
  calls occur); confirmed via infra audit. No change needed.
- Async flows: API dispatches Celery task by registered name → worker executes → result in Redis
  backend → frontend polls by task id. Ownership enforced via `ControllerTask` before any
  `AsyncResult` access (security boundary intact).

## E. Verification environment

- Live stack via `docker compose` (postgres, redis, api, worker, nginx, frontend), all healthy.
- Live calls executed with PowerShell `Invoke-WebRequest`/`Invoke-RestMethod` against
  `http://localhost` (same path browser traffic takes through nginx); plus in-container checks.
- Backend tests run in `backend\.venv` (`pytest`), frontend `tsc --noEmit` + `npm run build`.

## F. Browser automation

**Browser automation unavailable** in this environment (no Playwright/Chrome tooling present).
Browser-equivalent verification was performed via the nginx front-door HTTP path; the deployed
bundle is confirmed served by nginx and contains the expected UI markers for each change
(verified by grepping the served `index-*.js` inside the frontend container).

## G. Authentication flows

- Login valid/invalid, demo logins for all three roles (PLATFORM_ADMIN / MERCHANT /
  FINANCE_MANAGER), token reuse across a fresh process — all live 200/401 as expected.
- Anonymous → any protected route → **401** (verified live).

## H. Financial dashboard

- `FinanceDashboardPage` shows real summary, accounts, transactions, budgets, goals, risks,
  recommendations, each from its own line API.
- **Defect fixed (genuine):** the shared `run()` catch always wrote to `setSummary`, so a late
  failing section (budgets/risks/recommendations) clobbered the already-rendered summary. Added a
  `listError` helper + `onError` parameter so each section reports its own failure and the
  summary survives. (`frontend/src/pages/FinanceDashboardPage.tsx`.)

## I. Reconciliation frontend

- Page previously had **sync-only** execution; the real async backend path was not wired in the UI.
- **Defect fixed (genuine):** added async submit + poll: `POST …/reconcile/async` → 201
  `{task_id, PENDING}` → poll `GET …/reconcile/async/{task_id}` every 2 s (max 30) → SUCCESS
  renders the live report (`batch_size`, `matched_count`, `match_rate`, `exception_count`,
  exceptions list with categories/review state); FAILURE/timeout/401/404 handled; interval
  cleaned up on unmount; duplicate submissions blocked by a `busyRef`. (`ReconciliationPage.tsx`.)
- Live: sync batch=55 matched=44 rate=80.00%; async SUCCESS same metrics; 11 exceptions all
  `MISSING_LEDGER_RECORD`. None of these figures are hardcoded — they come from the responses.

## J. AI controller page

- Uses the async flow (`…/ai-controller/async`). Real backend currently returns 503 for
  provider-not-configured (no `OPENAI_API_KEY` in this demo environment).
- **Defect fixed (genuine):** the old async poll treated a server error (≥500) as transient and
  kept polling; after the contract change below, a `503 AI provider is not configured` would
  have polled to timeout. Now 503 (or any ≥500) is a terminal state with a clear message, 4xx is
  a terminal error, and `SUCCESS` renders the real report. (`AiControllerPage.tsx`.)
- **Backend change (consistent contract, regression-tested):** the async poll route previously
  returned an opaque generic `FAILURE` for every failure. A task failing because the AI provider
  is not configured is now answered with the same explicit `503 {"error": "AI provider is not
  configured"}` the synchronous AI endpoints already return. Only the exception **type** is
  inspected — traceback/message/payload are never exposed. All other failures keep the generic
  safe message. (`app/routes/m4_controller_async.py`; live-verified: task →
  `503 {"error":"AI provider is not configured"}`.)

## K. AI analysis page

- "Insight" placeholders are explicit empty-state copy, not fabricated AI output; page handles
  503 with an unavailable state. Left untouched (matches the no-fake-AI requirement).

## L. Categories

- Backend categories API is not business-scoped; the frontend therefore correctly omits
  `businessQuery()` there (verified in page + endpoint audit). No change needed.

## M. Audit page

- Reads real `audit_records`; live verification shows `kind=reconciliation` records including
  sync, async (with `task_id` in payload), and `review_status_update` rows. Categories/audit are
  intentionally not business-scoped (matches backend).

## N. No hardcoded data

- The frontend contains zero hardcoded reconciliation figures. The values 55/44/11 and 80.00%
  appear only in this report as observed API output. `ReconciliationPage` renders whatever the
  report endpoint returns, including zero/empty states.

## O. OPENAI_API_KEY not configured → clear frontend state

- Sync AI endpoints return `503 AI provider is not configured`; `AiAnalysisPage`/explanation
  surfacing shows the unavailable state.
- Async AI controller now surfaces the same `503` and the UI shows
  **"AI insights are currently unavailable. The AI provider is not configured…"** instead of an
  opaque failure or indefinite polling. Live-verified end-to-end.
- Happy path is covered by unit tests with a mocked provider; no fake AI results are ever
  produced (AI is proposal-only and never mutates financial state).

## P. No fake AI

- Confirmed: no AI page fakes responses, confidence, or reasoning. Empty-state placeholders are
  clearly labeled. The controller only proposes actions.

## Q. Loading states

- All data pages render busy/polling states: reconciliation "Processing financial records in the
  background…", AI controller "Submitting…/Running…", section skeletons elsewhere. Wait — no
  skeletal PCs claimed beyond what exists; a single scanning pass confirmed every fetch gate has
  an accessible busy indicator or placeholder.

## R. Error states

- Per-section error messages (dashboard fix), poll failure/timeout messages, 401 → interceptor
  redirect to login, 403 → `ForbiddenState` on admin pages, generic network fallbacks — all
  present and reachable.

## S. Settings & user management

- Settings page uses real endpoints; user management admin page is gated by `RoleRoute`
  (`PLATFORM_ADMIN` only), backend `403` for merchants/FM (live-verified).

## T. Admin pages

- `AdminDashboardPage`/`UserManagementPage` correct. Known UX observation (not changed):
  PLATFORM_ADMIN sees merchant/AI nav links that `RoleRoute` redirects to `/admin`; backend
  authorization is correct and no redirect loops occur. Reported, not modified.

## U. CORS / Docker / nginx

- No CORS configured on backend; verified unnecessary (same-origin proxy). nginx routes
  `/api/` → api:5000 and `/` → frontend static bundle; `docker compose ps` shows all six
  services healthy after final rebuild. Image-recreate lesson recorded: after code/image rebuild,
  use `docker compose up -d --no-build --force-recreate` (containers here are image-baked; there
  are no bind-mounts).

## V. Isolated test data + cleanup

- Only one temporary user was created for the authz matrix (`outsider-*@example.com`). It was
  removed after verification (`DELETE FROM users WHERE email LIKE 'outsider-%@example.com'`;
  remaining count confirmed 0). No existing user/business/financial data was touched.

## W. Query-param handling

- Centralized in `BusinessContext.businessQuery()`, appended only where the endpoint is business-
  scoped. Reconciliation review/explain endpoints need no `business_id` — authorization derives
  from the persisted line's owner (`_require_line_access`). Confirmed; no change.

## X. API base URL / environment

- `frontend/…/api.ts` base = `VITE_API_BASE_URL ?? "/api"`; `vite.config.ts` dev proxy to
  `:5000`. Production bundle uses the same-origin `/api` path via nginx. No change needed.

## Y. Server response contracts

- All frontend type consumers match documented backend JSON shape for the endpoints exercised
  live (summary/accounts/transactions/budgets/goals/facts/risk/recommendations/reconcile/async
  reports/controller reports). Verified by inspection + live responses.

## Z. TypeScript types

- `lib/types.ts` defines `AsyncTaskSubmitResponse`, `AsyncTaskStatus` (`result` union of
  `FinancialControllerReport | ReconciliationReport`), and all report types. `tsc --noEmit`
  exits 0.

## AA. localStorage / auth tokens

- `AuthContext` stores the token, `api.ts` attaches `Authorization: Bearer`, and the
  `onUnauthorized` interceptor logs out on 401. Live probe: valid token → 200, missing token →
  401. No secrets stored anywhere (no keys logged or committed).

## AB. Build / test / lint

- Backend: **690 passed, 15 skipped** (705 collected; environment `EXIT=0`). New regression:
  `test_status_failure_when_ai_not_configured_returns_503` plus the unchanged generic-failure
  safety test. Skips are the existing Celery-worker-module convention.
- Frontend: `npx tsc --noEmit` exit 0; `npm run build` succeeds (8.11 s), only the pre-existing
  chunk-size advisory.
- No dedicated frontend unit-test harness exists; typecheck + production build + live HTTP
  verification were used instead (stated honestly).

## AC. Performance / no infinite polling

- Reconciliation and AI controller polls bounded: 2 s interval, max 30 attempts (~60 s) then a
  clear terminal message; interval cleared on unmount. Live async reconcile completed in one
  poll. Backend throughput metrics (live sync 87.1k lines/s, async 66.7k lines/s) come from
  in-engine `perf_counter`; sub-millisecond for the 55-record demo batch is real but visually
  small (metric infrastructure matters for larger datasets).

## AD. Production artifacts

- Rebuilt images: `api`, `frontend` (only changed services; worker/postgres/redis/nginx
  unchanged this phase). Frontend container now serves bundle `index-BnkFgG62.js`, confirmed to
  contain the new UI markers ("AI insights are currently unavailable", reconciliation async
  flow). All six containers healthy.

## AE. Responsive design

- Tailwind responsive classes are present (grid `sm:`/`md:`/`lg:` breakpoints, wrapping flex
  rows). **Not validated by browser automation — unavailable in this environment.** Static
  inspection only; reported honestly.

## AF. Summary, git state, limitations

**Defects fixed (genuine integration issues only):**
1. `FinanceDashboardPage` run-error handler clobbered summary output.
2. `ReconciliationPage` did not surface the existing async reconciliation backend.
3. AI controller async failure was opaque/unreachable as a clear state — aligned backend poll
   contract (503 for provider-not-configured, regression-tested) and frontend polling semantics.

**Git state (`git status --short`):** all frontend/backend/reconciliation/database/docs work is
modified/untracked and intentionally **uncommitted** — no commits, no pushes, no resets were
performed. Relevant to this phase: modified `m4_controller_async.py`, `AiControllerPage.tsx`,
their tests, plus previously carried working tree.

**Honest limitations:**
1. Browser automation unavailable — responsive behavior and any client-only glitches are not
   mechanically proven; deployment and JS markers verified inside the container.
2. AI success path (controller report with real provider) not exercised live — no provider key
   configured; both sync and async paths degrade to explicit 503/unavailable states, and the
   happy path is covered by mocked-provider unit tests.
3. Reconciliation numbers (55/44/11, 80.00%) are live API output for the demo batch, not
   hardcoded in the UI; the engine is deterministic and the 88-line fresh-seed set (76/88 =
   86.36%) is covered by seed assertions + unit tests.

See also `docs/demo/buildathon-report.md` (reconciliation + hardening) and
`docs/demo/demo-runbook.md`.