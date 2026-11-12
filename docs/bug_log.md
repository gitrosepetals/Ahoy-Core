# Bug log

Product/code defects (not local-dev outages — those live in [incident_log.md](./incident_log.md)). Newest first. Every fix links the release in [iterations.md](./iterations.md) where it shipped.

**Status:** `Open` · `Fixed (x.y.z)` · `Won't fix (reason)`

---

## Entry template

```markdown
### BUG-NNN — Short title
- **Found:** YYYY-MM-DD (how: audit / test / pilot report)
- **Area:** file or feature ID
- **Symptom:** what the user or test sees
- **Root cause:** why
- **Fix:** what changed
- **Status:** Open | Fixed (x.y.z)
```

---

### BUG-008 — Publish tests fail when the dev DB has many old approved posts
- **Found:** 2026-11-12 (1.2.0 test run)
- **Area:** `tests/test_milestone_d_0_9.py` (`test_publish_due_posts_dev_mode`, `test_publish_live_ayrshare_request`) vs `services/publishing.py` `BATCH_LIMIT`
- **Symptom:** Test posts stay `approved` instead of `published`.
- **Root cause:** Tests share the dev database; 392 leftover approved posts fill the publish batch before the test post is reached.
- **Fix:** Both tests now call `_park_other_due_posts` first, which pushes pre-existing due posts into the future inside the test's own transaction (rolled back afterwards), so leftovers can't fill the batch. Other tests still leave approved posts behind in the dev DB (392 → 406 after one run); that no longer affects results.
- **Status:** Fixed (1.2.0) — `test_publish_due_posts_dev_mode`, `test_publish_live_ayrshare_request`

### BUG-007 — Manifest trail lags and runs off screen
- **Found:** 2026-11-01 (Captain report: "the treasure path scroll animation lags and then disappears off screen")
- **Area:** `apps/web/src/components/AhoyScrollProgress.tsx` (Ship Manifest)
- **Symptom:** Scrolling the Manifest stutters; the drawn tip of the dotted trail drifts above or below the visible screen, so the trail seems to vanish.
- **Root cause:** (1) every scroll frame called `setState`, re-rendering the page-height SVG; (2) the reveal was a page-size SVG mask with a 24px stroke, re-rasterized every frame; (3) reveal length = whole-page scroll fraction, which has no fixed relation to where the viewport is, so the tip left the screen.
- **Fix:** scroll handler writes straight to the DOM (progress bar transform + clip height) inside one rAF — no React renders while scrolling; mask replaced by a `clipPath` rectangle; the reveal ends at 65% of the viewport height (whole trail at the bottom of the page), so the tip is always on screen.
- **Status:** Fixed (1.1.0)

### BUG-006 — Every API call from the browser waited ~200 ms (Windows)
- **Found:** 2026-11-01 (Captain report: "it's so slow"; measured `/health` 210 ms via `localhost` vs 5 ms via `127.0.0.1`)
- **Area:** `NEXT_PUBLIC_API_BASE_URL`, `PUBLIC_API_BASE_URL` (env + code defaults)
- **Symptom:** Ship pages slow to fill in; each page makes several API calls, each ~200 ms slower than it should be.
- **Root cause:** `localhost` resolves to IPv6 `::1` first on Windows; uvicorn listens on IPv4 `127.0.0.1` only, so each new connection waits for the IPv6 attempt to fail before falling back.
- **Fix:** API addressed as `http://127.0.0.1:8000` in `.env.example` files, local `.env` / `.env.local`, and the code defaults (Google OAuth redirect left on `localhost` — it must match the registered URI). Existing local upload URLs rewritten.
- **Status:** Fixed (1.1.0)

### BUG-005 — Yelp review times stored without a timezone
- **Found:** 2026-11-01 (new unit test while building 0.11.0)
- **Area:** `apps/api/app/services/review_providers.py` `_parse_ts`
- **Symptom:** Yelp's `time_created` ("YYYY-MM-DD HH:MM:SS") parsed as a naive datetime → stored as if UTC, putting Yelp reviews up to 8h off (wrong day in the "new reviews" rollup).
- **Root cause:** Yelp documents these times in Pacific time with no offset; parser assumed every timestamp carried one.
- **Fix:** Naive timestamps are read in an explicit zone (`America/Los_Angeles` for Yelp).
- **Status:** Fixed (0.11.0) — never shipped; test `test_provider_parsers`

### BUG-004 — Ship pages hardcoded to the first client
- **Found:** 2026-11-01 (Phase 1 PRD audit)
- **Area:** `apps/web/src/app/ship/*` — 7 call sites of `me.clients[0]`
- **Symptom:** A Captain who owns more than one business can only ever see the first one; no way to switch.
- **Root cause:** Single-tenant assumption during Milestone C.
- **Fix:** Shared active-client helper (`lib/session.ts`) + header switcher; every Ship page reads the active client.
- **Status:** Fixed (0.12.0) — `pickActiveClient` / `activeClientId` in `lib/session.ts`, `ShipClientSwitcher` in the nav

### BUG-003 — Low-star review alert never fires
- **Found:** 2026-11-01 (Phase 1 PRD audit)
- **Area:** `apps/api/app/services/reviews.py` `flag_low_star_if_needed` (CL-05)
- **Symptom:** 1–3★ reviews get a draft but the Captain is never alerted by SMS/push.
- **Root cause:** Function defined but never called from any code path; `notify_captain_low_star_review` was also log-only.
- **Fix:** Call on review ingest when a new low-star review lands; real notification dispatch.
- **Status:** Fixed (0.8.0) — wired in `ensure_ai_reply`, deduped by `reviews.alerted_at`; test `test_bug003_low_star_alert_fires_once`

### BUG-002 — Twilio SMS send blocks the event loop
- **Found:** 2026-11-01 (Phase 1 PRD audit)
- **Area:** `apps/api/app/services/auth.py` `_send_twilio_sms`
- **Symptom:** With live Twilio, every magic-link request blocks all other API requests for the duration of the HTTP call to Twilio.
- **Root cause:** Synchronous `twilio.rest.Client.messages.create` called inside an `async def`.
- **Fix:** Shared async SMS sender (`services/sms.py`) over `httpx.AsyncClient`.
- **Status:** Fixed (0.8.0) — `services/sms.py` over `httpx.AsyncClient`; test `test_send_sms_is_async_httpx`

### BUG-001 — Mixed POS/estimate period drops estimated revenue
- **Found:** 2026-11-01 (Phase 1 PRD audit)
- **Area:** `apps/api/app/services/roi.py` `summarize_roi` (CL-01 / Story 2.1)
- **Symptom:** If even one day in the window has POS revenue, the headline becomes the POS sum only — every lead-based estimate from the other days vanishes, under-reporting revenue.
- **Root cause:** POS vs estimate decided per day (`pos_revenue > 0`) and the summary switched wholesale to `total_pos` when any day used POS. PRD says the switch is "if POS integration is active", i.e. per client.
- **Fix:** Decide once per client from `clients.pos_provider`; POS clients show `SUM(pos_attributed_revenue_usd)`, others show the formula.
- **Status:** Fixed (0.7.0) — regression test `test_bug001_estimate_not_dropped_on_partial_pos_days`
