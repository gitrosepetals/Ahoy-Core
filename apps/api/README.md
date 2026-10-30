# A-hoy API

FastAPI backend for the Ship (Captain) and Crew Deck.

## Setup

```bash
cd apps/api
cp .env.example .env
uv sync
```

Apply DB migrations (Postgres with `pgvector`):

```bash
psql "$DATABASE_URL_PSQL" -f ../../packages/db/migrations/001_initial_schema.sql
psql "$DATABASE_URL_PSQL" -f ../../packages/db/migrations/002_seed_oak_lawn.sql
```

Run:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs

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
