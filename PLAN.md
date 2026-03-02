## Implementation Runbook: Multi-Agent Delivery + Stage 1 Execution Spec

### Summary
You chose to implement in the current repo, so the first step is to **scaffold and harden the API foundation** (FastAPI + PostgreSQL + JWT + entitlement primitives + snapshot ingestion).  
This runbook is structured so multiple agents can work in parallel after Stage 1 is merged.

---

## Multi-Agent Stage Map

### Stage 1 (Agent A) - Platform Foundation **(implement now)**
- Bootstrap FastAPI service.
- Add config, logging, error model, API versioning (`/v1`).
- Add JWT auth middleware + admin RBAC primitive.
- Add PostgreSQL models + migrations for core tables.
- Add entitlement service (manual free/premium).
- Add financial snapshot ingest/read endpoints.
- Add unit/integration test harness + CI baseline.

### Stage 2 (Agent B) - Premium Deterministic Engines
- Health score engine.
- Debt/cashflow/goal feasibility engines.
- Simulation service core and typed scenario schemas.

### Stage 3 (Agent C) - Copilot + LLM Explanation Layer
- Intent whitelist router (15 premium templates).
- Structured compute-to-explanation pipeline.
- OpenAI adapter + policy guardrails.

### Stage 4 (Agent D) - Admin APIs
- Overview/subscription/usage/data-health dashboards.
- Manual plan updates + user controls + audit logging.

### Stage 5 (Agent E) - Family Mode + QA Hardening
- Household/family scoring APIs.
- Performance/rate limiting/observability.
- End-to-end regression suite.

---

## Stage 1 Detailed Implementation (Decision-Complete)

### 1) Repo Structure to Create
- `app/main.py`
- `app/api/v1/router.py`
- `app/api/v1/endpoints/health.py`
- `app/api/v1/endpoints/financial_snapshots.py`
- `app/core/config.py`
- `app/core/security.py`
- `app/core/errors.py`
- `app/core/logging.py`
- `app/db/session.py`
- `app/db/base.py`
- `app/db/models/{user_entitlement.py,financial_snapshot.py,admin_audit_log.py}`
- `app/schemas/{common.py,financial_snapshot.py,entitlement.py}`
- `app/services/{entitlements.py,financial_snapshots.py}`
- `alembic.ini`, `alembic/`, migration scripts
- `tests/{conftest.py,test_health.py,test_auth.py,test_financial_snapshots.py}`
- `requirements.txt`
- `README.md` update with run/test instructions

### 2) Initial Public API Contracts (Stage 1 only)
- `GET /v1/health`
  - 200: service status, version, db connectivity flag.
- `POST /v1/financial-snapshots`
  - Auth required (`user_id` from JWT).
  - Upsert by `(user_id, month)`.
  - Request includes: `month, income_total, expense_total, assets_total, liabilities_total, emi_total, liquid_assets, essential_expense, credit_limit_total, credit_outstanding_total`.
- `GET /v1/financial-snapshots/latest`
  - Returns latest snapshot for authenticated user.
- `GET /v1/entitlement/me`
  - Returns `{plan, status, expiry_date, source}`.
- `PATCH /v1/admin/subscriptions/{user_id}`
  - Admin-only manual plan update for MVP.

### 3) DB Schema (Stage 1)
- `user_entitlements`
  - `user_id (unique)`, `plan enum(free,premium)`, `status enum(active,inactive,expired)`, `expiry_date`, `source enum(manual)`, timestamps.
- `financial_snapshots`
  - `id`, `user_id`, `month(date first-day normalized)`, numeric fields above, timestamps, unique `(user_id, month)`.
- `admin_audit_logs`
  - `id`, `actor_user_id`, `target_user_id`, `action`, `payload_json`, timestamp.

### 4) Security + Validation Rules
- JWT verification via existing auth issuer/JWKS (config-driven).
- Reject missing/invalid JWT with typed error code.
- RBAC: admin routes require claim `role=admin`.
- Monetary fields must be `>= 0`.
- `month` must be valid `YYYY-MM` normalized to month start in storage.

### 5) Error Contract (uniform)
- Shape: `{error_code, message, details?, request_id}`.
- Stage 1 error codes:
  - `AUTH_INVALID_TOKEN`
  - `AUTH_FORBIDDEN`
  - `VALIDATION_ERROR`
  - `NOT_FOUND`
  - `DB_CONFLICT`
  - `INTERNAL_ERROR`

### 6) Testing for Stage 1
- Unit:
  - entitlement resolver behavior,
  - snapshot month normalization and validation.
- Integration:
  - auth pass/fail,
  - admin RBAC enforced,
  - snapshot upsert conflict/update behavior.
- API contract:
  - response shape and error code assertions for all Stage 1 endpoints.

### 7) Stage 1 Acceptance Criteria
- Service boots locally and exposes OpenAPI docs.
- Migrations run cleanly on empty Postgres.
- JWT-protected user endpoints functional.
- Admin subscription patch works and writes audit log.
- Snapshot upsert + latest retrieval pass integration tests.
- CI runs tests successfully.

---

## Agent Parallelization Rules After Stage 1
- Stage 2/3/4 can begin in parallel once:
  - DB base schema is merged,
  - auth middleware and entitlement service are stable,
  - snapshot ingestion contract is fixed.
- Shared interfaces to freeze before parallel start:
  - snapshot schema,
  - error contract,
  - entitlement response shape.

---

## Assumptions and Defaults
- This repo is currently empty and will become backend API repo.
- Free/premium source of truth is manual entitlement table (no billing webhook yet).
- REST `/v1` is the only contract line (no legacy adapter).
- OpenAI integration is deferred to Stage 3; Stage 1 is deterministic foundation only.
- Family mode remains later stage as planned.

