# Milestone A — Foundation (build log)

**Status:** Complete (local E2E sign-in verified after resolving port 5432 clash)  
**Goal:** Monorepo scaffold, Postgres schema + seed, magic-link auth (sign-in only), tenant scoping, push-token API + Capacitor shell.

Tracks implementation against [technical_implementation_plan.md](./technical_implementation_plan.md) § Phase 1 Milestone A.

**Incidents:** see [incident_log.md](./incident_log.md) (2026-10-30 Failed to fetch / dual Postgres on 5432).

---

## Checklist

| # | Item | Status | Notes |
|---|---|---|---|
| A1 | Monorepo scaffold (`apps/web`, `apps/api`, `apps/mobile`, `packages/db`) | Done | Workspaces + Capacitor shell |
| A2 | SQL migrations + Oak Lawn seed | Done | `packages/db/migrations/001_*`, `002_*` |
| A3 | Magic-link / OTP JWT auth + role gates | Done | `/auth/magic-link`, `/auth/verify`, `/auth/me`; `CaptainUser` / `CrewUser` deps |
| A4 | Multi-tenant `client_id` scoping | Done | `TenantClientId` + `GET /clients/{id}` |
| A5 | Push token registration + deep-link config | Done | `/devices/push-token`; Capacitor config + `SHIP_DEEP_LINK_PATHS` |
| A6 | CI + `.env` templates | Done | `.github/workflows/ci.yml`, root + app `.env.example` |
| A7 | Living docs | Done | This file + README + package READMEs |

---

## Layout

```text
/
  apps/web/          # Next.js — Ship (/ship) + Crew Deck (/crew) + auth
  apps/api/          # FastAPI — /api/v1/auth, /clients, /devices
  apps/mobile/       # Capacitor shell for the Ship
  packages/db/       # SQL migrations + Oak Lawn seed
  docs/              # Plans + this build log
```

---

## API surface (Milestone A)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | no | Liveness |
| POST | `/api/v1/auth/magic-link` | no | Request sign-in link (`dev_magic_link` when `AUTH_DEV_MODE=true`) |
| GET | `/api/v1/auth/verify?token=` | no | Exchange magic link → JWT (48h) |
| GET | `/api/v1/auth/me` | bearer | Current user + in-scope clients |
| GET | `/api/v1/clients` | bearer | List tenants in JWT scope |
| GET | `/api/v1/clients/{client_id}` | bearer + tenant | Single client; 403 if out of scope |
| POST | `/api/v1/devices/push-token` | bearer | Upsert device push token |
| DELETE | `/api/v1/devices/push-token?token=` | bearer | Disable push token |

**Auth vs nudge:** Magic link is **sign-in only**. Everyday “batch ready” nudges are push (wired later); tokens are stored now.

**Roles:** `captain` | `crew` | `deckhand` | `admin` (replaces PRD `client_owner` / `account_captain` / `field_creator`).

---

## Web routes

| Path | Audience |
|---|---|
| `/` | Landing |
| `/auth/sign-in` | Request magic link |
| `/auth/verify` | Consume token, store JWT, redirect |
| `/ship` | Captain home (stub + push register button) |
| `/crew` | Crew Deck client list (stub) |

---

## Seed identities (Oak Lawn)

| Role | Email | Phone | ID |
|---|---|---|---|
| Captain | `dr.nguyen@oaklawnoptometry.example` | `+15551234001` | `11111111-1111-1111-1111-111111111111` |
| Crew | `jordan@ahoy.example` | `+15551234002` | `22222222-2222-2222-2222-222222222222` |
| Client | Oak Lawn Optometry | — | `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` |

---

## How to run

```bash
# 1) Env
cp .env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local

# 2) Database (Docker optional)
docker compose up -d db
# or manually:
# psql "$DATABASE_URL_PSQL" -f packages/db/migrations/001_initial_schema.sql
# psql "$DATABASE_URL_PSQL" -f packages/db/migrations/002_seed_oak_lawn.sql

# 3) API
cd apps/api && uv sync && uv run uvicorn app.main:app --reload --port 8000

# 4) Web
cd apps/web && npm install && npm run dev
```

Open http://localhost:3000/auth/sign-in → phone `+15551234001` → use returned **Dev link**.

```bash
# Tests / lint (A-hoy Postgres must be up for DB-backed tests)
cd apps/api && uv run pytest && uv run ruff check app tests
cd apps/web && npm run lint
```

### Pytest markers (A / B / A↔B)

| Command | What it proves |
|---|---|
| `uv run pytest -m milestone_a` | Auth, tenancy 403, push token, health/hash — no Brand Brain |
| `uv run pytest -m milestone_b` | Brand Brain, media, generate/release/approve (sign-in only as setup) |
| `uv run pytest -m milestone_c` | ROI, swap, approve-all, reviews |
| `uv run pytest -m integration_ab` | A sessions + role/tenant gates across the B Crew→Captain pipeline |
| `uv run pytest -m integration_abc` | A auth + B pipeline + C ROI/swap/approve-all/reviews |
| `uv run pytest` | All of the above (CI) |

Isolated A suite: `apps/api/tests/test_milestone_a.py` (see [incident_log.md](./incident_log.md) for the auth incident that motivated these regressions).

---

## Troubleshooting (quick)

| Symptom | Likely cause | Check / fix |
|---|---|---|
| Sign-in **Failed to fetch** | API 500 (often DB); browser hides detail | `curl http://localhost:8000/health`; try magic-link; see [incident_log.md](./incident_log.md) |
| `password authentication failed for user "postgres"` with Compose “correct” password | **Another Postgres on 5432** (e.g. `postgresql-x64-18`) | `Get-Service *postgres*`; `netstat -ano \| findstr :5432`; stop local service or move Compose to 5433 |
| Compose: `Skipping initialization` | Volume already existed | Schema may still be fine; or apply migrations manually / `docker compose down -v` once |
| Confused why web is 3000 but errors mention 5432 | Three processes | UI **3000**, API **8000**, DB **5432** |

---

## Change log

### 2026-10-30

- Scaffolded monorepo: `apps/web` (Next.js 15), `apps/api` (FastAPI + uv), `apps/mobile` (Capacitor config), `packages/db`.
- Wrote migrations with Captain/Crew theme roles + MVP gap tables; Oak Lawn seed.
- Implemented magic-link auth (dev mode), JWT sessions, role gates, tenant-scoped client routes, push-token register/disable.
- Ship / Crew Deck / auth UI stubs; deep-link path helpers; CI workflow; env examples; root README.
- Documented progress in this file (living build log per request).
- **Incident:** sign-in Failed to fetch caused by Windows `postgresql-x64-18` + Docker both on 5432; fixed by stopping local service. Logged in [incident_log.md](./incident_log.md).
- Pytest markers: isolated `milestone_a` suite in `test_milestone_a.py`; see also `milestone_b` / `integration_ab`.

---

## Out of scope (later milestones)

Brand Brain, campaign generator, Treasure Map UI, approval queue, Reputation Radar, Ayrshare publish, Stripe, live APNs/FCM send.
