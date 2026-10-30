# Incident / troubleshooting log

Running log of local-dev and ops issues. Newest first.

---

## 2026-10-30 — Sign-in “Failed to fetch” (port 5432 clash)

**Symptom:** On `/auth/sign-in`, submitting Captain phone `+15551234001` showed **Failed to fetch**. Web on `:3000` loaded; API `/health` on `:8000` was fine.

**What it looked like (red herrings):**
1. Docker Desktop “not running” early on → Compose could not start.
2. After Compose was up, logs said `Skipping initialization` → worried seed/schema never ran (schema/seed were actually present later).
3. Config said password `postgres` in both `.env` and `docker-compose.yml`, so password mismatch seemed impossible.
4. `ALTER USER postgres WITH PASSWORD 'postgres'` inside the Docker container did not fix host connections.

**Root cause:** **Two Postgres servers bound to port 5432.**

| Process | Role |
|---|---|
| Windows service `postgresql-x64-18` (`postgres.exe`) | Local install; answered most `localhost:5432` connections from the API |
| Docker container `ahoymarketingplatform-db-1` | Real A-hoy DB (migrations + Oak Lawn seed) |

The API’s `DATABASE_URL` pointed at `localhost:5432`, which hit **Windows Postgres**, not Docker. That instance rejected `postgres`/`postgres` → API returned **500**. The 500 lacked a usable CORS header from the browser’s point of view → UI showed **Failed to fetch** instead of the real DB error.

**Ports reminder (not the bug, but easy to confuse):**

| Port | Service |
|---|---|
| 3000 | Next.js Ship / Crew UI |
| 8000 | FastAPI |
| 5432 | Postgres (must be the *A-hoy* instance) |

**Fix that worked:**
```powershell
Get-Service *postgres*
Stop-Service postgresql-x64-18
# optional while developing A-hoy:
# Set-Service postgresql-x64-18 -StartupType Manual
```
Confirm Docker DB still up: `docker ps` → `ahoymarketingplatform-db-1`. Restart API if needed; sign-in with `+15551234001` again.

**Why `Get-Service` only showed one Postgres:** Docker’s DB is a **container**, not a Windows service. Use `docker ps` for it.

**Prevention / alternatives:**
- Prefer stopping or disabling local `postgresql-x64-*` while using Compose on 5432, **or**
- Map Compose to another host port (e.g. `5433:5432`) and set `DATABASE_URL` / `DATABASE_URL_PSQL` to `:5433`.
- If Compose says `Skipping initialization` on a fresh project, either apply `packages/db/migrations/*.sql` manually or `docker compose down -v` once to re-run init (only when wiping data is OK).

**Related docs:** [milestone_a.md](./milestone_a.md)

**Regression test:** `apps/api/tests/test_auth_captain_crew.py` — magic-link → verify → `/me` for seeded Captain (`+15551234001`) and Crew (`+15551234002`). Skips if `DATABASE_URL` is unreachable (wrong Postgres / service down).
