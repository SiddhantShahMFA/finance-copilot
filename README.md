# finance-copilot

Stage 1 API foundation for Finance Copilot using FastAPI + SQLAlchemy + Alembic.

## Setup

```bash
uv venv
uv pip install -e .[dev]
```

## Environment Variables

```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/finance_copilot
JWT_ISSUER=finance-copilot
JWT_AUDIENCE=finance-copilot-client
JWKS_URL=https://your-auth-domain/.well-known/jwks.json
JWT_SECRET_KEY=dev-secret
JWT_ALGORITHM=HS256
API_VERSION=v1
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=10
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_PATH_PREFIXES=/v1/copilot/query,/v1/simulations/run,/v1/family
```

Notes:
- `JWKS_URL` is optional. If set, JWT verification can use JWKS keys.
- `JWT_SECRET_KEY` fallback is useful for local and test environments.

## Run Migrations

```bash
uv run alembic upgrade head
```

## Run API

```bash
uv run uvicorn app.main:app --reload
```

## Run Tests

```bash
uv run pytest -q
```

## Stage 1 Endpoints

- `GET /v1/health`
- `POST /v1/financial-snapshots`
- `GET /v1/financial-snapshots/latest`
- `GET /v1/entitlement/me`
- `PATCH /v1/admin/subscriptions/{user_id}`

## Stage 2 Endpoints

- `GET /v1/health-score`
- `GET /v1/debt/insights`
- `GET /v1/cashflow/insights`
- `GET /v1/goals/feasibility`
- `POST /v1/simulations/run`

## Stage 3 Endpoints

- `POST /v1/copilot/query`

## Stage 4 Endpoints

- `GET /v1/admin/overview`
- `GET /v1/admin/subscriptions`
- `GET /v1/admin/ai-usage`
- `GET /v1/admin/data-health`
- `GET /v1/admin/observability`
- `POST /v1/admin/users/{user_id}/suspend`
- `POST /v1/admin/users/{user_id}/reset-password`

## Stage 5 Endpoints

- `POST /v1/family/households`
- `POST /v1/family/households/{household_id}/members`
- `POST /v1/family/households/{household_id}/goals`
- `GET /v1/family/overview?household_id=<id>`
