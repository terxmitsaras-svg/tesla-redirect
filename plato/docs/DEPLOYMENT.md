# PLATO — Running & deploying

## Local development (no Docker)

Requirements: Python 3.12+, Node 20.9+.

```bash
# API (SQLite by default, simulated provider enabled)
cd plato/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Web
cd plato/frontend
cp .env.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                       # http://localhost:3000
```

## Docker (Postgres + Redis + API + web)

```bash
cd plato
cp .env.example .env
# set PLATO_JWT_SECRET and PLATO_ENCRYPTION_KEY (command in the file)
docker compose up --build
```

Web: http://localhost:3000 · API: http://localhost:8000 · API docs: http://localhost:8000/docs

`NEXT_PUBLIC_API_URL` is baked into the web bundle at build time (compose build arg).

## Tests

```bash
cd plato/backend && ruff check app tests && pytest -q           # unit, API, orchestration, wire-level adapters
cd plato/frontend && npm run typecheck && npm run build
# Browser end-to-end (needs both servers running, simulated provider enabled):
cd plato/frontend && WEB_URL=http://localhost:3000 npm run e2e
```

## Live provider demo (§10, real API calls)

```bash
export ANTHROPIC_API_KEY=… OPENAI_API_KEY=… PLATO_DEMO_OPENAI_MODEL=<chat model your key can use>
python plato/backend/scripts/live_demo.py --api http://localhost:8000
```

Or in the UI: **Providers** → paste keys (verified live) → open a project → add an agent on
Anthropic Claude and one on OpenAI → enter an objective → **Start run**.

## Production checklist

| Item | Setting |
|---|---|
| Environment | `PLATO_ENV=production` (refuses to start with default secrets or the simulated provider) |
| Secrets | `PLATO_JWT_SECRET` (≥ 32 random bytes), `PLATO_ENCRYPTION_KEY` (Fernet). Store in a secrets manager (AWS Secrets Manager, GCP Secret Manager, Vault, Doppler) and inject as env vars. Rotating the Fernet key requires re-encrypting `provider_credentials`. |
| Simulated provider | `PLATO_ENABLE_MOCK_PROVIDER=false` |
| Database | managed PostgreSQL; `PLATO_DATABASE_URL=postgresql+asyncpg://…` |
| Redis | `PLATO_REDIS_URL=redis://…` (event fan-out across API instances) |
| CORS | `PLATO_CORS_ORIGINS=https://app.your-domain` |
| TLS | terminate at the load balancer; WebSockets need upgrade support and idle timeout ≥ 120 s |
| Scaling | runs execute in the API process that started them — use **sticky sessions** (e.g. by project) when running more than one API replica, until execution moves to workers |
| Stripe | create Products/Prices; set each plan's `stripe_price_id` via `PATCH /api/admin/plans/{code}`; set `PLATO_STRIPE_SECRET_KEY`, `PLATO_STRIPE_WEBHOOK_SECRET`; point a webhook at `/api/billing/webhook` for `checkout.session.completed`, `customer.subscription.created/updated/deleted`, `invoice.paid`; enable the Customer Portal for plan changes. Optional usage meter: `PLATO_STRIPE_METER_EVENT_NAME` (value = USD × 10 000). |
| Admins | `PLATO_ADMIN_EMAILS=you@company.com` (granted at sign-up) |
| Pricing | add real per-model prices for non-Anthropic models via `PLATO_MODEL_PRICING_JSON`, otherwise a fallback estimate ($5/$20 per MTok) is used and flagged |
| Rate limiting | in-process limiter; put an edge limiter (load balancer / API gateway) in front for multi-instance deployments |
| Migrations | tables are created at startup; adopt Alembic before the first schema change in production |
