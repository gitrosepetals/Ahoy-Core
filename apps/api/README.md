# A-hoy API

FastAPI backend for the Ship (Captain) and Crew Deck.

## Setup

```bash
cd apps/api
cp .env.example .env
uv sync
```

Apply DB migrations (Postgres with `pgvector`) — all files in `packages/db/migrations/` in order (see `packages/db/README.md`); e.g.:

```bash
psql "$DATABASE_URL_PSQL" -f ../../packages/db/migrations/001_initial_schema.sql
psql "$DATABASE_URL_PSQL" -f ../../packages/db/migrations/002_seed_oak_lawn.sql
```

Run:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

Background jobs (publishing, queue reminders/expiry, later rollups and review sync):

```bash
uv run python -m app.worker          # loop
uv run python -m app.worker --once   # run every job once
```

or set `EMBEDDED_WORKER=true` to run the loop inside the API process (single instance only is fine either way — jobs take a Postgres advisory lock).

Endpoint overview: [docs/technical_implementation_plan.md § Key API Surface](../../docs/technical_implementation_plan.md#key-api-surface-fastapi). Provider setup: [docs/integrations_setup.md](../../docs/integrations_setup.md).

## Milestone A endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | Liveness |
| POST | `/api/v1/auth/magic-link` | no | Request sign-in link (dev returns `dev_magic_link`) |
| GET | `/api/v1/auth/verify?token=` | no | Exchange magic link for JWT |
| GET | `/api/v1/auth/me` | bearer | Current user + clients |
| GET | `/api/v1/clients` | bearer | Tenant list in scope |
| GET | `/api/v1/clients/{client_id}` | bearer + tenant | Single client (scoped) |
| POST | `/api/v1/devices/push-token` | bearer | Register Ship push token |
| DELETE | `/api/v1/devices/push-token` | bearer | Disable push token |

See [docs/milestone_a.md](../../docs/milestone_a.md) for the build log.
