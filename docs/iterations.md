# Iterations log

Living build log for **every product/engineering slice**, including work that is not a milestone checklist item (polish, merges, test hardening, CI). Newest first.

Milestone gates still have their own logs ([milestone_a.md](./milestone_a.md), [milestone_b.md](./milestone_b.md), [milestone_c.md](./milestone_c.md)). Outages stay in [incident_log.md](./incident_log.md).

**Standing rule:** end every coding slice with an entry here. If the slice also closes milestone checklist items, update that milestone file too — do not fold polish-only work into a closed milestone’s checklist as if it were new C/D scope.

---

## Entry template

```markdown
## YYYY-MM-DD — Short title

**Why:** one line

**What shipped:**
- …

**How to try:** (omit if not user-facing)

**Tests:** (omit if untouched)

**Related:** optional links
```

---

## 2026-10-30 — Test matrix + A↔B↔C integration

**Why:** Run milestones in isolation and together; catch role/tenant regressions across A→B→C; keep CI honest.

**What shipped:**
- Pytest markers: `milestone_a`, `milestone_b`, `milestone_c`, `integration_ab`, `integration_abc` ([apps/api/pyproject.toml](../apps/api/pyproject.toml))
- Shared helpers + seeded IDs ([apps/api/tests/helpers.py](../apps/api/tests/helpers.py))
- New [apps/api/tests/test_integration_abc.py](../apps/api/tests/test_integration_abc.py) (ROI → generate/release → swap → approve-all → review reply + tenancy)
- Split Milestone C cases: swap vs approve-all; seeded low-star review id; Crew forbidden on swap
- CI runs each marker then full suite ([.github/workflows/ci.yml](../.github/workflows/ci.yml)); Ruff ignores for FastAPI `Depends`/`File`/`Form` defaults

**Tests:**
```powershell
cd apps/api
uv run pytest -m milestone_a
uv run pytest -m milestone_b
uv run pytest -m milestone_c
uv run pytest -m integration_ab
uv run pytest -m integration_abc
uv run pytest
uv run ruff check app tests
```

**Related:** [milestone_a.md](./milestone_a.md), [milestone_b.md](./milestone_b.md), [milestone_c.md](./milestone_c.md)

---

## 2026-10-30 — Ship Posts + Queue merge

**Why:** Two Captain feeds (Queue vs Posts) were redundant; one actionable Posts screen.

**What shipped:**
- `/ship/posts` — tabs All / Awaiting you / Approved; Approve, Request edit, Swap media, Approve all on `pending_client` ([apps/web/src/app/ship/posts/page.tsx](../apps/web/src/app/ship/posts/page.tsx))
- Legacy `/ship/queue` → redirect `?tab=pending`
- Ship nav: Home, Posts, Media, Reviews (Queue link removed)
- Push/notify deep links → `/ship/posts?tab=pending`
- Mobile README path note

**How to try:** Captain `+15551234001` → `/ship/posts`. Open `/ship/queue` and confirm redirect.

**Related:** [milestone_c.md](./milestone_c.md) (C2 polish surface; merge is post-checklist UX)

---

## 2026-10-30 — Crew UX polish (type, media upload, Posts tabs)

**Why:** Make Crew Deck readable and match the staged draft → release → approved mental model.

**What shipped:**
- Geist on body, larger base type, `.ahoy-prose` / `.ahoy-muted` on Crew + Ship surfaces
- Crew media: **Upload photo** + thumbnails (below Brand Brain)
- Crew **Posts** tabs: Drafts / Awaiting Captain / Approved (replaces mixed queue table)

**How to try:** Crew `+15551234002` → client page → Brand Brain → Media → Generate drafts → Posts tabs → Release.

**Related:** [milestone_b.md](./milestone_b.md)

---

## 2026-10-30 — Approval refill path documented + test

**Why:** Captains need a clear path after approving empties the awaiting list.

**What shipped:**
- Docs for generate → release refill after approve
- `test_approve_leaves_queue_and_refill_via_generate_release` (`milestone_b`)

**How to try:** Approve all awaiting posts as Captain → Crew Generate + Release → posts reappear under Awaiting you.

**Related:** [milestone_b.md](./milestone_b.md)
