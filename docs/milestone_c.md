# Milestone C — The Ship (build log)

**Status:** Done (local)  
**Goal:** Treasure Map ROI, polished approval queue, Reputation Radar, Ship bottom nav.

Tracks [technical_implementation_plan.md](./technical_implementation_plan.md) § Milestone C.

---

## Checklist

| # | Item | Status |
|---|---|---|
| C1 | ROI API + Treasure Map home | Done |
| C2 | Queue polish: swap media, approve all | Done |
| C3 | Reviews seed + list + approve-reply | Done |
| C4 | Ship bottom nav (Home, Posts, Media, Reviews; Calendar stub) | Done |
| C5 | Tests + docs | Done |

---

## How to try

1. Captain `+15551234001` → `/ship` Treasure Map (tap revenue for daily breakdown).
2. `/ship/posts` — merged feed + approvals (tabs All / Awaiting you / Approved). Approve, request edit, swap media, Approve all on awaiting items. Legacy `/ship/queue` redirects here.
3. `/ship/reviews` — approve the low-star reply draft.
4. `/ship/media` — read-only vault; `/ship/calendar` stub (points to Posts until D).

Apply review seed if needed:

```powershell
$env:PGPASSWORD='postgres'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -d ahoy -f packages/db/migrations/004_seed_oak_lawn_reviews.sql
```

```powershell
cd apps/api
uv run pytest -m milestone_a
uv run pytest -m milestone_b
uv run pytest -m milestone_c
uv run pytest -m integration_ab
uv run pytest -m integration_abc
uv run pytest
```

Capacitor / TestFlight: sync `apps/mobile` against `apps/web` export when ready for device pilots; store listing not required for this slice.

---

## API (new in C)

| Method | Path |
|---|---|
| GET | `/clients/{id}/roi?days=` |
| GET | `/clients/{id}/roi/breakdown` |
| POST | `/queue/{post_id}/swap-asset` |
| POST | `/clients/{id}/queue/approve-all` |
| GET | `/clients/{id}/reviews` |
| POST | `/reviews/{id}/approve-reply` |

---

## Change log

### 2026-10-30

- Shipped Milestone C local: ROI/Treasure Map, queue swap + approve-all, reviews seed `004`, Ship bottom nav, `milestone_c` pytest.
- Captain **Posts** (`/ship/posts`) — merged history + approval actions; Queue nav removed (`/ship/queue` redirects).
