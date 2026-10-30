# A-hoy Marketing Platform

Hybrid Software-with-a-Service platform: **Captains** (SMB owners) use the **Ship** mobile/web app; **Crew** runs marketing from the **Crew Deck**.

## Docs

| Doc | Purpose |
|---|---|
| [docs/technical_implementation_plan.md](docs/technical_implementation_plan.md) | Full technical plan |
| [docs/milestone_a.md](docs/milestone_a.md) | **Living build log for Milestone A** (update as you ship) |
| [docs/incident_log.md](docs/incident_log.md) | Troubleshooting / incident history (e.g. port 5432 clash) |
| [business docs/](business%20docs/) | PRD + strategy playbook |
| [packages/db/README.md](packages/db/README.md) | Migrations |

## Monorepo

```text
apps/web      Next.js — Ship + Crew Deck UI
apps/api      FastAPI — auth, tenancy, devices
apps/mobile   Capacitor shell for the Ship
packages/db   Postgres migrations + seed
```

## Quick start

1. Copy [`.env.example`](.env.example) → `apps/api/.env` and `apps/web/.env.local`.
2. Start Postgres (`docker compose up -d db` if Docker is available) and confirm migrations/seed applied.
3. API: `npm run dev:api` (or `cd apps/api && uv run uvicorn app.main:app --reload --port 8000`)
4. Web: `cd apps/web && npm install && npm run dev`
5. Sign in as Captain with phone `+15551234001` (`AUTH_DEV_MODE=true` returns a clickable magic link).

## Current phase

**Phase 1 Milestone A — Foundation** (see [docs/milestone_a.md](docs/milestone_a.md)).
