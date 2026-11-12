# A-hoy Marketing Platform

Hybrid Software-with-a-Service platform: **Captains** (SMB owners) use the **Ship** mobile/web app; **Crew** runs marketing from the **Crew Deck**.

## Docs

| Doc | Purpose |
|---|---|
| [docs/technical_implementation_plan.md](docs/technical_implementation_plan.md) | Full technical plan |
| [docs/iterations.md](docs/iterations.md) | **Living release log** — every version, what shipped and why |
| [docs/milestone_d.md](docs/milestone_d.md) | Milestone D (pilot hardening + Phase 1 PRD gaps): checklist + design decisions |
| [docs/integrations_setup.md](docs/integrations_setup.md) | Vendor setup for Twilio, Firebase, OpenAI, Ayrshare, Google, Facebook, Yelp, Stripe, Sentry |
| [docs/deployment.md](docs/deployment.md) | Deploy to Vercel + Railway + Supabase: env vars, webhooks, go-live checklist |
| [docs/bug_log.md](docs/bug_log.md) | Code defects found and fixed |
| [docs/milestone_a.md](docs/milestone_a.md) · [b](docs/milestone_b.md) · [c](docs/milestone_c.md) | Earlier milestone build logs |
| [docs/incident_log.md](docs/incident_log.md) | Troubleshooting / incident history (e.g. port 5432 clash) |
| [business docs/](business%20docs/) | PRD + strategy playbook |
| [packages/db/README.md](packages/db/README.md) | Migrations |

## Monorepo

```text
apps/web      Next.js — Ship + Crew Deck UI
apps/api      FastAPI API + background worker (python -m app.worker)
apps/mobile   Capacitor shell for the Ship
packages/db   Postgres migrations + seed
```

## Quick start

1. Copy [`.env.example`](.env.example) → `apps/api/.env` and `apps/web/.env.local`.
2. Start Postgres (`docker compose up -d db` — a fresh volume runs every migration; an existing one needs the new files applied, see [packages/db/README.md](packages/db/README.md)).
3. API: `npm run dev:api` (or `cd apps/api && uv sync && uv run uvicorn app.main:app --reload --port 8000`). Worker: `uv run python -m app.worker`, or set `EMBEDDED_WORKER=true`.
4. Web: `cd apps/web && npm install && npm run dev`
5. Sign in as Captain with phone `+15551234001` (`AUTH_DEV_MODE=true` returns a clickable magic link).

## Current phase

**Phase 1 Concierge MVP — code complete (1.0.0).** Milestones A–D done; next is the 5–10 client pilot (see [docs/integrations_setup.md](docs/integrations_setup.md) go-live checklist and the Crew Deck KPI panel). Phase 2 (AG-02 media multiplier, CL-04 Flare Gun, CL-03 shoot scheduler) is not started.

Vocabulary: **Captain** = the business owner, **Ship** = the app the Captain uses, **Crew** = the A-hoy team on the Crew Deck.
