# Milestone B — Crew Deck core (build log)

**Status:** Done (local)  
**Goal:** Brand Brain CRUD, campaign generate → `content_queue`, release to Captain, thin revision loop.

Tracks [technical_implementation_plan.md](./technical_implementation_plan.md) § Milestone B.

---

## Checklist

| # | Item | Status |
|---|---|---|
| B1 | Brand Brain GET/PUT + embedding (LLM_DEV_MODE stub) | Done |
| B2 | Media list/upload + campaign generate | Done |
| B3 | Release drafts → `pending_client` + notify stub | Done |
| B4 | Captain approve / request-edit revision loop | Done |
| B5 | Crew + Ship UI | Done |
| B6 | Tests + docs | Done |

---

## How to try

1. Sign in as Crew (`+15551234002`) — use **Use Crew** on `/auth/sign-in` so you land on `/crew` (not Ship).
2. On Crew Deck click **Brand Brain & campaigns** for Oak Lawn (URL `/crew/clients/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`). Brand Brain is that page’s first section — not on `/crew` itself.
3. Edit Brand Brain → Save (embedding recomputed in `LLM_DEV_MODE`).
4. Scroll past Brand Brain to **Media vault** → **Upload photo** (thumbnails show for uploads and seeded placeholders). Or apply migration `003`.
5. Check assets → **Generate drafts** → see them under **Posts → Drafts** → **Release to Captain** (moves to **Awaiting Captain**).
6. Sign in as Captain (`+15551234001`) → `/ship/posts` (Awaiting you) → Request edit / Approve → Crew **Posts → Approved**.

Defaults: `LLM_DEV_MODE=true` (no OpenAI required). Set `OPENAI_API_KEY` and `LLM_DEV_MODE=false` for live captions.

Apply media seed if needed:

```powershell
$env:PGPASSWORD='postgres'
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -U postgres -d ahoy -f packages/db/migrations/003_seed_oak_lawn_media.sql
```

---

## Approval queue (Captain)

`/ship/posts` shows pending + approved; actions (Approve / Request edit) only on **`pending_client`**.

| Action | Result |
|---|---|
| **Approve** | Status → `approved`. Post **leaves** the Ship queue. (Publish to socials is later / Milestone D.) |
| **Request edit** | LLM rewrites caption (dev stub prefixes `[DEV revised]`). Status usually stays `pending_client` so the same card stays in the queue with new copy. If rewrite fails → `changes_requested` (Crew follow-up; not shown on thin Ship queue). |

### Getting items back into the queue

There is **no unapprove** UI. After you approve everything, refill like this:

1. Sign in as **Crew** → Oak Lawn client page.
2. **Generate drafts** → **Release to Captain**.
3. Sign in as **Captain** → `/ship/posts` again.

Optional local SQL reset (dev only):

```sql
UPDATE content_queue
SET status = 'pending_client'
WHERE client_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
  AND status = 'approved';
```

Regression coverage: `apps/api/tests/test_milestone_b.py` (marker `milestone_b`), including `test_approve_leaves_queue_and_refill_via_generate_release`.

### Pytest markers (A / B / A↔B)

| Command | What it proves |
|---|---|
| `uv run pytest -m milestone_a` | Auth/tenancy/push only (no generate) |
| `uv run pytest -m milestone_b` | Brand Brain, media, queue filters, generate/release/revision |
| `uv run pytest -m milestone_c` | ROI, swap, approve-all, reviews |
| `uv run pytest -m integration_ab` | A magic-link + roles still protect B Brand Brain → release → edit → approve |
| `uv run pytest -m integration_abc` | A auth + B pipeline + C ROI/swap/approve-all/reviews |
| `uv run pytest` | Full suite (CI) |

Shared helpers: `apps/api/tests/helpers.py`.

---

## Readable UI type

Product surfaces use Geist via `layout.tsx` + `globals.css` (base ~17px, slate foreground). Helpers:

- `.ahoy-prose` — primary reading text (captions, forms)
- `.ahoy-muted` — secondary copy (still ≥ ~15px, slate-700)

Ship queue and Crew Brand Brain / queue table use these so captions and labels stay readable.

---

## API surface (Crew / Captain)

| Method | Path | Role |
|---|---|---|
| GET/PUT | `/api/v1/clients/{id}/brand-profile` | Crew (GET also Captain) |
| GET/POST | `/api/v1/clients/{id}/media` | Crew (+ Captain list) |
| POST | `/api/v1/clients/{id}/media/upload` | Crew |
| POST | `/api/v1/clients/{id}/campaigns/generate` | Crew |
| GET | `/api/v1/clients/{id}/queue?status=` | Crew + Captain |
| POST | `/api/v1/clients/{id}/queue/release` | Crew |
| POST | `/api/v1/queue/{post_id}/approve` | Captain |
| POST | `/api/v1/queue/{post_id}/request-edit` | Captain |

Uploads served at `http://localhost:8000/uploads/...`.

---

## Change log

### 2026-10-30

- Started and shipped Milestone B: models, LLM/notify services, routers, Crew client page, Ship queue, pytest (`LLM_DEV_MODE`), env keys, media seed `003`.
- Documented approval / refill-queue path; added `test_approve_leaves_queue_and_refill_via_generate_release`.
- Readable type: apply Geist on body, bump base size, `.ahoy-prose` / `.ahoy-muted` on Ship queue + Crew forms.
- Test matrix: `milestone_a` / `milestone_b` / `integration_ab` markers, helpers, isolated + A↔B integration suites.
- Media vault polish: **Upload photo** button + thumbnails on Crew client page (below Brand Brain).
- Crew **Posts** tabs: Drafts / Awaiting Captain / Approved (replaces mixed Content queue table).
