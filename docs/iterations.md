# Iterations log

Living build log for **every product/engineering slice**, including work that is not a milestone checklist item (polish, merges, test hardening, CI). Newest first.

**Current version:** `1.2.0`

Versioning: bump **patch** for docs/tests/CI-only; **minor** for user-facing polish or API surface; reserve **major** for milestone-aligned releases (A/B/C/D). Milestone gates still have their own logs ([milestone_a.md](./milestone_a.md), [milestone_b.md](./milestone_b.md), [milestone_c.md](./milestone_c.md)). Outages stay in [incident_log.md](./incident_log.md); code defects in [bug_log.md](./bug_log.md).

**Standing rule:** end every coding slice with a new version entry here (and bump **Current version**). If the slice also closes milestone checklist items, update that milestone file too — do not fold polish-only work into a closed milestone’s checklist as if it were new C/D scope.

---

## Entry template

```markdown
## X.Y.Z — Short title

**Why:** one line

**What shipped:**
- …

**How to try:** (omit if not user-facing)

**Tests:** (omit if untouched)

**Bugs:** (omit if none) BUG-NNN found / fixed — see bug_log.md

**Related:** optional links
```

---

## 1.2.0 — Deploy readiness: pluggable file storage + API Dockerfile

**Why:** Uploads were written to the API host's local disk, which is wiped on every redeploy on Railway/Fly, so media and voice notes would vanish in production.

**What shipped:**
- **`services/storage.py`:** one `save_file()` for media photos and voice notes. `STORAGE_BACKEND=local` (default, unchanged dev behaviour) or `supabase` (Supabase Storage REST, public bucket). New env: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET`.
- **`apps/api/Dockerfile` + `.dockerignore`:** one image for the API and the worker (worker overrides the start command with `python -m app.worker`).
- **[deployment.md](./deployment.md):** step-by-step Vercel + Railway + Supabase setup, env var table, webhooks, go-live checklist.

**How to try:** local flow is unchanged. To test production storage, set the three Supabase vars and `STORAGE_BACKEND=supabase`, upload a photo in Crew, and confirm the URL points at `supabase.co/storage`.

**Tests:** 3 new unit tests (`test_storage_1_2.py`: local write, Supabase request shape, config/error handling); ruff clean. Full suite 73 passed. Two publishing tests had been failing because 392 leftover approved posts in the local dev DB exceeded the publish batch limit; fixed in the tests (BUG-008). Docker image and live Supabase upload were **not** built or run.

**Bugs:** BUG-008 found / fixed (test isolation) — see bug_log.md

---

## 1.1.0 — Faster Ship: API address fix + smooth Manifest trail

**Why:** The Captain reported the app was slow and the Manifest's treasure-path trail lagged and disappeared off screen.

**What shipped:**
- **~200 ms saved per API call on Windows:** the web app and media URLs now use `http://127.0.0.1:8000` instead of `localhost:8000` (BUG-006).
- **Trail rewritten for scroll performance:** no React re-renders while scrolling, `clipPath` reveal instead of a page-size mask, and the trail's tip stays at ~65% of the screen height while you scroll; the full trail shows at the bottom of the page (BUG-007). Scroll progress bar updated the same way.

**How to try:** restart the API and `npm run dev` (env changes are read at start-up), hard-refresh `/ship/posts`, scroll fast up and down.

**Tests:** 70 API tests passed; web `tsc` + lint clean. Trail behaviour checked by code review only — not yet verified visually in a browser.

**Bugs:** BUG-006, BUG-007 fixed.

---

## 1.0.0 — Milestone D complete: Phase 1 Concierge MVP is pilot-ready

**Why:** Closes [Milestone D](./milestone_d.md) — every Phase 1 gap from the 2026-11-01 PRD audit (0.7.0–0.15.0) is shipped, plus the tooling to run and measure the 5–10 client pilot. Major bump per the versioning rule.

**What shipped:**
- **Pilot KPIs (PRD §7):** `GET /kpis` (Crew) + "Pilot KPIs" panel on the Crew Deck — avg time-to-approve vs < 48h, share approved within 48h, Captains active (30 days) vs > 85%, logo churn vs < 4%, per client with billing status.
- **[integrations_setup.md](./integrations_setup.md):** vendor-side walkthrough for Twilio, Firebase, OpenAI, Ayrshare, Google Business Profile, Facebook, Yelp, Stripe and Sentry — env vars, per-client Crew steps, how to verify — plus a per-client go-live checklist.
- **Docs refresh:** technical plan (Milestone D done, full API surface, worker schedule, status machine with `expired`), README (docs index, worker, current phase, Captain/Ship/Crew vocabulary), API README, Milestone D Phase 1 coverage table + known follow-ups.

**Phase 1 release train:** 0.7.0 correctness → 0.8.0 notifications → 0.9.0 worker + publishing → 0.10.0 ROI data → 0.11.0 reviews → 0.12.0 Ship (switcher, voice, PWA) → 0.13.0 Stripe → 0.14.0 terminology → 0.15.0 audit + Sentry → 1.0.0.

**How to try:** Crew `+15551234002` → `/crew` → Pilot KPIs panel (approve a few posts as the Captain first).

**Tests:** `tests/test_milestone_d_1_0.py` (time-to-approve, 48h share, Captain activity, Crew-only `/kpis`). 70 API tests passed; web `tsc`, lint and production build clean.

**Bugs:** none new. Open bugs: none (BUG-001…005 fixed).

**Known follow-ups:** email/SMS campaign sender; Blob/S3 media with signed URLs; native Capacitor push registration; frontend automated tests.

---

## 0.15.0 — Audit log, Sentry, structured logs

**Why:** Pilot hardening — when a Captain asks "who approved that?" or a job fails at 3am, we need a record and an alert. [Milestone D](./milestone_d.md) D13.

**What shipped:**
- **Audit log (`services/audit.py`, table `audit_events`):** automatic capture of every post / review status change with actor (Captain, Crew, system job, webhook); credential saves (field names only); Stripe tier/status changes. Crew `GET /clients/{id}/audit` + "Ship's log" panel on the client berth.
- **Sentry:** API (`sentry-sdk[fastapi]`), worker job failures, and web (`@sentry/browser`, lazy-loaded) — all off unless a DSN is set; no PII.
- **Structured logs:** `LOG_FORMAT=json`, `LOG_LEVEL`; shared `app/observability.py` for API + worker.
- **Single version source:** `app.__version__` (API title version + Sentry release).
- Migration `011_audit_log.sql`; settings `LOG_FORMAT`, `LOG_LEVEL`, `SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`, `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT`; new deps `sentry-sdk[fastapi]` (API), `@sentry/browser` (web).

**How to try:** apply `011_audit_log.sql`; generate → release → approve a post; Crew → client berth → "Ship's log" shows created → pending_client (crew) → approved (captain).

**Tests:** `tests/test_milestone_d_0_15.py`: JSON formatter; full post trail with correct actor per step + Crew-only feed; credential audit never contains the secret. 69 API tests passed; web `tsc` + lint clean.

**Bugs:** none.

---

## 0.14.0 — Terminology sweep: Captain, Ship, Crew

**Why:** The Captain asked that the theme hold everywhere: **Captain** = business owner, **Ship** = the app, **Crew** = the A-hoy team. Copy added in 0.8–0.13 drifted to "owner", "your OK" and plain "notifications".

**What shipped:**
- **SMS / push:** sign-in "Ahoy, Captain! Tap to board your Ship"; posts ready "Ahoy, Captain! N new posts for <business> are on your Manifest awaiting your mark"; reminder "Captain, N posts … need your mark before <day> or they stay in port"; low-star "Storm on the Radar: 2★ review" / "Captain, <name> left …".
- **Ship:** Radar statuses "Awaiting the Captain's mark", "· needs the Captain", "Captain replied on google"; Map "Turn on Ship alerts", "Your Ship's plan"; Logbook "Everything the Captain cleared for sail".
- **Crew Deck:** "send it to the Captain", "Connect Google (Captain signs in)".
- **Docs:** Milestone D wording ("owner" → "Captain"); vocabulary recorded as a design decision. API/code keep "client".

**Tests:** new `tests/test_milestone_d_0_14.py` asserts every Captain notification says "Captain" and never "owner" / "your OK". `temp_client` fixture teardown fixed for tests that roll back. 66 API tests passed; web `tsc` + lint clean.

**Bugs:** none (test-fixture teardown issue fixed in passing).

---

## 0.13.0 — Stripe billing: plans, customer portal, ad-spend pass-through

**Why:** `subscription_tier` was a hand-set enum and nothing billed anyone; PRD §4 calls for Stripe Billing with recurring tier management and ad-spend pass-through. [Milestone D](./milestone_d.md) D11.

**What shipped:**
- **`services/billing.py`** (Stripe REST, idempotency keys): customer per client, Checkout session for a tier, customer-portal session, ad-spend invoice items, webhook signature check, event handler.
- **API (`routers/billing.py`):** `GET /clients/{id}/billing`, `POST /clients/{id}/billing/checkout` `{tier}`, `POST /clients/{id}/billing/portal`, `POST /clients/{id}/billing/ad-spend` (Crew), `POST /webhooks/stripe`.
- **Webhooks** keep `tier`, `subscription_status`, `current_period_end` and the Treasure Map's `billing_anchor_day` in sync; `invoice.payment_failed` → `past_due`; duplicates ignored via `stripe_events`.
- **Ship:** "Your plan" card on the Treasure Map (tier, status, renewal) with **Manage billing** → Stripe portal.
- **Crew:** Billing panel — status, choose tier → **Create checkout link** (copied to send to the Captain), **Bill ad spend**.
- Migration `010_stripe_billing.sql`; settings `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_HARBOR|CRUISER|FLAGSHIP`.

**How to try:** Stripe test mode: create 3 monthly prices, set the env vars, `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`, Crew → Billing → Create checkout link → pay with 4242 4242 4242 4242 → tier/status update on both screens.

**Tests:** `tests/test_milestone_d_0_13.py`: signature (valid, tampered, wrong secret, stale, missing), tier↔price mapping, checkout/portal/ad-spend requests via mock transport (customer reused, cents rounding, Crew-only ad spend, 400 when unconfigured), webhook → tier/status/anchor/period + duplicate + payment failed. 65 API tests passed; web `tsc` clean.

**Bugs:** none.

---

## 0.12.0 — Ship: business switcher, voice-note edits, swipe to approve, installable PWA

**Why:** Owners with two businesses were stuck on the first (BUG-004); Story 1.2's voice note, Story 1.1's swipe/instant next card and the PRD's PWA + push were missing. [Milestone D](./milestone_d.md) D12. (The planned 0.12.0 is split: Stripe moves to 0.13.0, audit log + Sentry to 0.14.0.)

**What shipped:**
- **Business switcher:** `lib/session.ts` `pickActiveClient` / `activeClientId`; `ShipClientSwitcher` in the Ship nav (only with 2+ businesses). Every Ship page (Map, Manifest, Logbook, Vault, Radar) uses the active business. Fixes BUG-004.
- **Voice notes:** "🎙️ Voice note" next to Request edit (tap to record, tap to send, 30s cap) → `POST /queue/{id}/request-edit-voice` → Whisper transcript → AI rewrite (dev: stub transcript). Crew's Needs crew tab plays the note when the AI couldn't handle it.
- **Faster approvals:** swipe a card right to approve; approve updates the card in place instead of reloading the Manifest.
- **PWA:** `app/manifest.ts` (standalone, start `/ship`, icons incl. maskable + Apple touch icon generated from the brand mark), `public/sw.js` (FCM background push + notification click → deep link), `PwaRegister`; "Turn on notifications" on the Map requests permission, gets an FCM token (`firebase` SDK, lazy-loaded) and registers it — falls back to a dev stub when Firebase isn't configured.
- New web env `NEXT_PUBLIC_FIREBASE_CONFIG`, `NEXT_PUBLIC_FIREBASE_VAPID_KEY`; new web dependency `firebase`; `uploads/*/voice/` git-ignored.

**How to try:**
1. `cd apps/web && npm install`.
2. Captain → Manifest → on an awaiting post press 🎙️ Voice note, speak, press ■ Stop & send → caption is rewritten.
3. On a phone (or devtools touch mode), swipe a card right → Approved.
4. Chrome → install icon in the address bar on `/ship`.

**Tests:** `tests/test_milestone_d_0_12.py`: voice note → dev transcript → rewrite → stored + served audio; unsupported type 415, >2 MB 413, Crew 403. Web: `npm run build` + `tsc --noEmit` clean. 61 API tests passed.

**Bugs:** BUG-004 fixed.

---

## 0.11.0 — Reputation Radar for real: review sync + reply posting

**Why:** Reviews were seed rows and "auto-replied" only meant a status flag — nothing was read from or posted to Google, Facebook or Yelp, and the PRD's optional 24-hour delay didn't exist. PRD CL-05; [Milestone D](./milestone_d.md) D10.

**What shipped:**
- **Providers (`services/review_providers.py`):** Google Business Profile (reviews, reply, locations, Performance API), Facebook Page ratings (+ comment reply), Yelp (read-only).
- **Sync (`services/reviews.py`):** worker job `sync_all_reviews` every 30 min (+ Crew "Sync reviews now"); new reviews are drafted with the full Brand Brain; owner-answered reviews imported as `skipped`.
- **Replies:** 4–5★ → `scheduled` until `reply_due_at` (client delay, default 24h) then posted by `post_due_review_replies` (5 min); 1–3★ → Captain. Captain can **edit**, **Approve & post** / **Send now**, or **Don't reply** (`POST /reviews/{id}/skip-reply`; approve accepts `reply_text`). Yelp shows **Copy reply**.
- **Google OAuth:** `GET /clients/{id}/integrations/google/start` → Google consent → `/integrations/google/callback` stores the refresh token (encrypted) → Crew picks the location. Facebook: `PUT /clients/{id}/integrations/facebook`.
- **GBP Performance:** `sync_gbp_performance` (6h) fills impressions / clicks / direction requests for the Detailed View.
- **Ship Radar** shows source, stars, editable draft, and a plain-English status ("Auto-reply posts Tue 9:00 AM — skip or send now", "Reply posted …", "Yelp doesn't allow app replies — copy this").
- **Crew:** connect Google, choose location, Facebook Page id + token, Yelp business id, auto-reply delay.
- Migration `009_review_sync.sql`; settings `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `YELP_API_KEY`.

**How to try:**
1. Apply `009_review_sync.sql`.
2. Locally (nothing connected) the seeded reviews still work: the 2★ shows an editable draft → Approve & post (dev-posts).
3. Live Google: set the Google OAuth env vars, Crew → Connect Google → Choose location → Save → Sync reviews now.

**Tests:** `tests/test_milestone_d_0_11.py`: Google/Facebook/Yelp parsers (mock transport), GBP performance parser, ingest (5★ scheduled +24h, 2★ alert once, owner-answered skipped, re-ingest idempotent), due-reply posting, Yelp → manual, live Google reply request, Captain edit/approve/skip + Crew sync, Google OAuth start/forged state/callback stores token, performance upsert. Shared `temp_client` fixture moved to `conftest.py`. 59 passed.

**Bugs:** BUG-005 found and fixed before release (Yelp timestamps).

---

## 0.10.0 — Closed-loop ROI: call tracking, form leads, itemized breakdown

**Why:** The Treasure Map's numbers were three seeded rows. PRD CL-01 / Story 2.1 need real tracked calls (over 60s) and form leads, and a breakdown "showing the exact call recordings/logs and form submissions that made up the number". [Milestone D](./milestone_d.md) D9.

**What shipped:**
- **Twilio call tracking (`routers/webhooks.py`):** `POST /webhooks/twilio/voice` (TwiML forward + optional recording with consent notice), `/voice/complete` (talk time, status, recording URL), `/recording` (late recording callback). Signature validation (`services/twilio_sig.py`).
- **Form leads:** `POST /webhooks/forms/{key}` for client websites (HTML form or JSON), honeypot, thank-you redirect.
- **Lead store + rollup (`services/leads.py`):** `lead_events` ORM (table existed since 001, unused until now); hourly worker job `rollup_daily_metrics` counts qualified calls (>= 60s), forms, directions and new reviews per client-local day.
- **Itemized breakdown:** `GET /clients/{id}/roi/leads` + recording proxy; Ship revenue card now opens "How we got this number" listing every call (time, talk time, counted / not counted, caller, ▶ Play recording) and form (name, contact, message), then the daily rows.
- **Detailed View (CL-01):** summary gains `detail` (impressions, clicks, CTR, direction requests, cost per lead); Ship toggle, hidden by default, remembered per device.
- **Crew:** client settings add forward-to number, record calls, timezone and show the Twilio Voice webhook + website form URLs to wire; "Manual metrics" entry for ad spend / impressions / clicks / directions (`PUT /clients/{id}/roi/manual`).
- ROI summary now uses the client's local "today" (timezone), matching the rollup.
- Migration `008_lead_tracking.sql`; new dependency `tzdata` (Windows has no system tz database).

**How to try:**
1. Apply `008_lead_tracking.sql`; `uv sync`.
2. Simulate a call: `curl -X POST localhost:8000/api/v1/webhooks/twilio/voice/complete -d CallSid=CA1 -d To=<tracking #> -d DialCallDuration=90` after setting a tracking number in Crew → Client settings, then `uv run python -m app.worker --once`.
3. Simulate a form: `curl -X POST localhost:8000/api/v1/webhooks/forms/oaklawn-demo-form-key -d name=Pat -d email=pat@example.com`.
4. Captain → `/ship` → tap the revenue card.

**Tests:** `tests/test_milestone_d_0_10.py`: qualification threshold, signature round trip, voice → TwiML (forward, consent, record) → completion (idempotent retry) → rollup counts only the 75s call, unknown number, signature enforced when live, form endpoint (JSON, redirect, honeypot, validation, unknown key), itemized leads + Crew-only manual metrics + Detailed View CTR. 51 passed.

**Bugs:** none new. (Timezone edge in two 0.7.0 tests fixed by using the client's local date.)

---

## 0.9.0 — Background worker + Ayrshare auto-publish

**Why:** Approved posts never left the building — nothing published at `scheduled_publish_at`, and 0.8.0's reminders/expiry had nothing to run them. PRD CL-02 "auto-publishes approved items at scheduled times"; [Milestone D](./milestone_d.md) D7–D8.

**What shipped:**
- **Worker (`app/worker.py`):** asyncio loop, jobs `publish_due_posts` (60s), `send_expiry_reminders` (5m), `expire_overdue_posts` (5m). Advisory-locked per job; `--once` mode; optional `EMBEDDED_WORKER=true` runs it inside the API lifespan.
- **Publishing (`services/publishing.py`):** Ayrshare `/api/post` with the client's profile key; Instagram (post/Reel), Facebook, TikTok, Google Business (`gmb`); media URL from the vault asset. Sets `published` + `published_external_id`. 3 attempts then `publish_failed`. Email/SMS flagged for manual send. Dev mode (no `AYRSHARE_API_KEY`) fakes success.
- **Encrypted credentials (`services/credentials.py`):** Fernet-encrypted `integration_credentials` (first use of that table).
- **Crew onboarding API:** `GET/PATCH /clients/{id}/settings` (tracking number, GBP location, POS provider, ticket value, conversion rate, billing day), `GET /clients/{id}/integrations`, `PUT /clients/{id}/integrations/ayrshare`, `POST /queue/{id}/publish-retry`, `POST /queue/{id}/mark-published`.
- **Crew UI:** "Client settings & integrations" panel (incl. Ayrshare key, write-only); Approved tab shows Scheduled / Published / Retrying / Publish failed / Send manually with Retry and Mark sent.
- **Ship Logbook (`/ship/calendar`):** no longer a stub — approved + published posts grouped by day with time, channel and "Sailed ✓".
- New dependency `cryptography`; new settings `AYRSHARE_API_KEY`, `PUBLISH_MAX_ATTEMPTS`, `CREDENTIALS_ENCRYPTION_KEY`, `EMBEDDED_WORKER`.

**How to try:**
1. `cd apps/api && uv sync`.
2. Generate (Days=1), release, approve as Captain; once its time passes run `uv run python -m app.worker --once` → the post shows "Sailed ✓" in the Ship Logbook. First local run also flushes any old approved test posts whose time has passed.
3. Live: set `AYRSHARE_API_KEY`, paste the client's profile key in Crew → Client settings.

**Tests:** `tests/test_milestone_d_0_9.py`: credential encryption + wrong key, Ayrshare body per channel, dev-mode publish (published / manual / TikTok fail → `publish_failed` after max attempts / future untouched), live request headers + body via mock transport, advisory lock skip, Crew settings + integrations (secret never echoed, Captain 403, validation), retry + mark-published. 45 passed.

**Bugs:** none new.

---

## 0.8.0 — Real notifications, 48h queue link, expiry reminders, low-star alerts

**Why:** Every Captain notification was a `NOTIFY_STUB` log line, so in a pilot nobody would ever hear that posts were ready, about to expire, or that a bad review landed. PRD CL-02 / Story 1.1 / CL-05; [Milestone D](./milestone_d.md) D5–D6.

**What shipped:**
- **Dispatcher (`services/notify.py`):** push via Firebase Cloud Messaging (new `services/push.py`, HTTP v1, works for iOS/Android/web tokens; invalid tokens auto-disabled) → SMS fallback via Twilio → dev log. Every attempt is stored in the new `notifications` table.
- **Async SMS (`services/sms.py`):** Twilio REST over `httpx.AsyncClient`; used by both sign-in links and notifications. Fixes BUG-002.
- **Story 1.1:** "posts ready" SMS includes a single-use magic link valid **48 hours** that signs the Captain in and opens `/ship/posts?tab=pending` directly.
- **Queue expiry (CL-02):** new `expired` status at the post's publish time; Crew **Expired** tab with reschedule (`PUT /queue/{id}/caption` now takes `scheduled_publish_at`). Job `send_expiry_reminders` sends one "needs your OK before <day>" message per client 48h before posts expire; `expire_overdue_posts` flips overdue ones. (Scheduled by the job runner in 0.9.0.)
- **Low-star alert (CL-05):** first time a 1–3★ review is drafted it alerts the Captain once, with the drafted reply preview and a link to `/ship/reviews`. Fixes BUG-003.
- **Crew:** `GET /clients/{id}/notifications` + "Captain notifications" panel on the client berth (kind · channel · status · body · error).
- Migration `007_notifications_queue_expiry.sql`; new settings `NOTIFY_LINK_TTL_HOURS`, `QUEUE_REMINDER_HOURS_BEFORE`, `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_FILE` (in `.env.example`).

**How to try:**
1. Apply `007_notifications_queue_expiry.sql`.
2. Crew: generate + release. The berth's "Captain notifications" shows `queue_ready · log · logged` with the 48h link in the body — open it in a private window: you land on the Captain's pending posts already signed in.
3. Live SMS: set `TWILIO_*` and `AUTH_DEV_MODE=false` (Twilio test credentials work).

**Tests:** `tests/test_milestone_d_0_8.py`: async SMS request shape (mock transport), SMS gating, release → notification + 48h link that verifies into the queue, reminder once-per-client/once-per-post + window + quiet period, expiry → Crew reschedule (and Captain can't approve expired), BUG-003 alert once. Integration AB updated for the new channel names. 38 passed.

**Bugs:** BUG-002 fixed, BUG-003 fixed.

---

## 0.7.0 — Phase 1 correctness: ROI, Brand Brain, multi-channel campaigns

**Why:** The 2026-11-01 PRD audit found Phase 1 features that ran but did not match the spec: revenue could under-report, prompts ignored most of the Brand Brain, the generator covered 3 of 5 channels with no SEO/hashtags, and Crew had no way to see or fix AI-flagged revisions. Opens [Milestone D](./milestone_d.md) (D1–D4).

**What shipped:**
- **ROI (CL-01 / Story 2.1):** POS vs estimate decided per client from `pos_provider` (not per day); headline defaults to the **current billing period** (`clients.billing_anchor_day`), `?days=N` still works as a rolling window. Summary adds `period`, `period_start`, `period_end`, `qualified_call_min_seconds` (60). Treasure Map shows "Since <date> (this billing period)" and the correct formula text.
- **Brand Brain (AG-01):** new `pricing_notes`, `seasonal_offers`, `local_seo_keywords` fields (migration `006`, Crew editor). New `BrandContext` puts the *whole* profile — business, voice, compliance, services, pricing, seasonal offers, ZIPs, SEO keywords — into every caption, revision **and** review-reply prompt. PUT only overwrites the new fields when sent.
- **Campaign generator (AG-03):** Crew can pick any of Instagram post/Reel, Facebook, TikTok, Google Business update, Email newsletter; `fan_out` makes one formatted variation per channel per slot (shared `batch_id`, 60-post cap). Per-channel rules: local hashtags on IG/TikTok/FB, plain-text local-SEO GBP updates, Subject/Preview for email. Prompt no longer forbids hashtags.
- **Asset tagging:** uploads are tagged by a vision model (live) or filename hints (dev) into PRD categories (staff, exterior, interior, product, testimonial, event) instead of `["uploaded"]`.
- **Revision loop (Story 1.2):** Crew **Needs crew** tab lists edit requests the AI could not rewrite, shows the Captain's feedback, and allows a hand edit (`PUT /queue/{id}/caption`) that sends the post back to the Captain.
- **CI:** API job now runs a pgvector Postgres service and applies every migration, so DB tests actually run in CI (previously all skipped). Compose mounts the whole migrations folder.
- API version string bumped to 0.7.0 (was stale at 0.3.0).

**How to try:**
1. Apply `packages/db/migrations/006_brand_brain_billing_period.sql` (see `packages/db/README.md`).
2. Crew `+15551234002` → client berth: fill Pricing / Seasonal offers / SEO keywords, save; tick all channels with "One version per channel" on, Generate — each slot gets IG, FB, TikTok, GBP and email variants.
3. Captain `+15551234001` → `/ship`: revenue card reads "Since Nov 1 (this billing period)".

**Tests:** `tests/test_milestone_d_0_7.py` (marker `milestone_d` + `unit`): billing-period math, BrandContext prompt, dev tags, BUG-001 regression, ROI default period, partial brand PUT, fan-out formatting, Crew caption edit. 32 passed.

**Bugs:** BUG-001 fixed (mixed POS/estimate period). BUG-002..004 logged from the audit.

**Related:** [milestone_d.md](./milestone_d.md), [bug_log.md](./bug_log.md)

---

## 0.6.93 — Fix Ruff import format in API main

**Why:** CI `uv run ruff check app tests` failed (I001) after adding the marketing router.

**What shipped:**
- Multiline `app.routers` import in `apps/api/app/main.py`

**How to try:** `cd apps/api && uv run ruff check app tests`

---

## 0.6.92 — Transparent SVG mark; nav-only on welcome

**Why:** PNG mark had a paper background; large page logo competed with the hero wordmark.

**What shipped:**
- `AhoyMark` redrawn as transparent SVG (sail chevron + pennant + hull)
- `/welcome` shows the mark only in the top nav; hero is wordmark + copy

**How to try:** Open `/welcome` — logo in header only; no boxed background.

---

## 0.6.91 — Welcome landing + email capture

**Why:** Platform gate alone doesn’t explain A-hoy services to prospects.

**What shipped:**
- Public `/welcome` with boat mark hero, Bridge/Engine Room, niches, Harbor/Cruiser/Flagship
- Email acquisition form → `POST /api/v1/marketing/leads` + `marketing_leads` migration
- `/` keeps Ship/Crew gate; “New here? See A-hoy” → `/welcome`

**How to try:** Open `/welcome`, submit an email; confirm row in `marketing_leads`. Apply `005_marketing_leads.sql` if needed.

---

## 0.6.90 — Trail no longer vanishes on long scroll

**Why:** ResizeObserver + pathLength remounts wiped the trail when scrolling far/fast.

**What shipped:**
- Reveal via `pathLength={1}` (no length flicker)
- SVG grows with page height without rebuilding the path
- Debounced layout; stop observing `documentElement` resize-on-scroll

**How to try:** Hard-refresh Manifest and scroll hard to the bottom — trail should stay drawn.

---

## 0.6.89 — No waves on Manifest

**Why:** Manifest should be trail-only; waves competed with the slither.

**What shipped:**
- ShipAtmosphere turns off deck waves on Manifest / queue

**How to try:** Open Manifest — grey trail only, no bottom waves.

---

## 0.6.88 — Trail stays on fast scroll; prior opacity

**Why:** Fast scroll re-rendered the mask at ~0 length so the trail vanished; opacity felt too strong.

**What shipped:**
- Reveal length tied to scroll progress in React (no reset to empty)
- Restored previous dotted stroke opacity / dash pattern

**How to try:** Hard-refresh Manifest and fling-scroll — trail should keep its drawn length.

---

## 0.6.87 — Trail in-frame and more visible

**Why:** Slither swung off-screen and was too faint to notice.

**What shipped:**
- Amp clamped inside the viewport with edge margin
- Stronger stroke, denser dashes, higher opacity (light + dark)

**How to try:** Hard-refresh Manifest — grey trail should stay on-screen and read clearly in the gutters.

---

## 0.6.86 — Smoother, faster Manifest trail

**Why:** Trail rebuilt + binary-searched on every scroll, so draw felt laggy.

**What shipped:**
- Path rebuilds only on layout change; scroll only updates reveal (DOM dasharray)
- Linear scroll→length mapping; softer longer curves, fewer segments

**How to try:** Hard-refresh Manifest and scroll — trail should draw smoothly without hitching.

---

## 0.6.85 — Randomized Manifest trail

**Why:** Path felt identical every visit.

**What shipped:**
- Each session gets a unique L↔R downward slither — random swing length, width, and curve ease
- Seeded so scrolling doesn’t reshuffle mid-page

**How to try:** Hard-refresh Manifest a few times — trail shape/size should change, still left↔right and down.

---

## 0.6.84 — Trail clears Manifest header text

**Why:** Slither started through the Manifest title/subtitle.

**What shipped:**
- Trail starts below the header block, out in the left gutter

**How to try:** Hard-refresh Manifest — grey trail should miss the copy under the title.

---

## 0.6.83 — Shared Manifest column width

**Why:** Feed vs List used different max-widths, so the toggle jumped.

**What shipped:**
- Both layouts share one `max-w-lg` column and the same chrome padding

**How to try:** Manifest → toggle Feed / List — toolbar stays put.

---

## 0.6.82 — Manifest Feed / List toggle

**Why:** Keep both the social feed and the earlier compact list.

**What shipped:**
- Feed vs List chooser on Manifest (persists in localStorage)
- Same approve / edit / swap actions in both layouts

**How to try:** Manifest → switch Feed / List in the toolbar.

---

## 0.6.81 — Manifest as social feed

**Why:** Queue cards read like an admin list, not a captain’s content feed.

**What shipped:**
- Feed posts: avatar + business name, square media, caption under image, status badge
- Narrow feed column; relative timestamps; actions under each post when awaiting

**How to try:** Open Manifest — scroll a social-style feed of posts to approve.

---

## 0.6.80 — Drop Crew lantern glow

**Why:** Red silhouette ball on Crew was unwanted.

**What shipped:**
- Removed the swaying lantern glow from Crew atmosphere

**How to try:** Hard-refresh `/crew` — kelp/copper hawsers only, no red orb.

---

## 0.6.79 — Crew wave colors

**Why:** Crew hawsers shared Captain’s grey/crimson and didn’t read as Crew.

**What shipped:**
- Hawser bands use kelp + copper (indigo fitting) instead of fg/lantern

**How to try:** Hard-refresh `/crew` — teal and indigo ropes, not grey/crimson.

---

## 0.6.78 — Subtle Crew, still solid

**Why:** Softening Crew reintroduced beaded “dots” via round caps on stretched SVGs.

**What shipped:**
- Captain-level opacity/fill kept
- Solid continuous strokes only (`butt`/`miter`, explicit `strokeDasharray="none"`)

**How to try:** Hard-refresh `/crew` — quiet solid hawsers, no dots.

---

## 0.6.77 — Subtler Crew atmosphere

**Why:** Crew hawsers/lantern were louder than Captain’s quiet waves.

**What shipped:**
- Matched Ship wave opacities (0.14 / 0.22) and stroke weight
- Softer lantern glow + gentler sway; vignette/band size aligned with Ship

**How to try:** Hard-refresh `/crew` — ropes should sit as quiet as Ship waves.

---

## 0.6.76 — No beads on Crew ropes

**Why:** Dual round-cap strands looked like random dots when the SVG stretched.

**What shipped:**
- One solid stroke per hawser; butt caps (no dash, no double strand)

**How to try:** Hard-refresh `/crew` — clean solid scrolling lines only.

---

## 0.6.75 — Solid Crew hawsers

**Why:** Dashed rope strands read as dotted lines.

**What shipped:**
- Hawser strokes are solid (no dash pattern)

**How to try:** Hard-refresh `/crew` — solid scrolling ropes only.

---

## 0.6.74 — Crew hawsers + lantern sway

**Why:** Crew needed its own pirate motion — not a copy of Captain’s sea waves.

**What shipped:**
- Scrolling dual-strand rope/hawser bands (same scroll engine as Ship)
- Soft pennant-crimson lantern glow that sways above the berth

**How to try:** Hard-refresh `/crew` — ropes scroll at the bottom; lantern light rocks gently.

---

## 0.6.73 — Crew waves only, no grid

**Why:** Chart grid cluttered Crew; only the animated bands were wanted.

**What shipped:**
- Removed chart grid / rule lines from Crew atmosphere
- Kept the three scrolling wave bands + vignette

**How to try:** Hard-refresh `/crew` — animated waves only, no grid.

---

## 0.6.72 — Crew atmosphere actually visible

**Why:** Chart backdrop was nearly invisible (and easy to miss without a hard refresh).

**What shipped:**
- Stronger chart grid + lantern/kelp corner washes
- Three scrolling bands (fg / kelp dashed / lantern), thicker strokes, taller bottom band
- Lighter vignette so motion isn’t washed out

**How to try:** Hard-refresh `/crew` or Brand Brain — grid + scrolling chart bands should be obvious like Ship waves.

---

## 0.6.71 — Clear animated Crew bands

**Why:** Crew backdrop was too faint and barely moved vs Captain’s scrolling waves.

**What shipped:**
- Same dual scrolling bottom bands as Ship (16s / 24s), with chart rules + dashed course line
- Clearer grid field; vignette matched to Ship so the motion stays readable

**How to try:** Open `/crew` — chart grid + scrolling ops bands should read as clearly as Ship waves.

---

## 0.6.70 — Crew chart-room background

**Why:** Crew was sharing Ship sea waves; operators need a workspace feel.

**What shipped:**
- Crew layout backdrop: chart grid, kelp rigging lines, soft lantern wash (no ocean waves)
- Removed Ship waves from Brand Brain; both `/crew` and client berths use `CrewAtmosphere`

**How to try:** Open `/crew` or a client Brand Brain — chart/ops desk behind content, not rolling waves.

---

## 0.6.69 — Trail on Manifest; waves on Brand Brain

**Why:** Trail belonged only on Manifest; Brand Brain needed the deck waves.

**What shipped:**
- Grey slither only on Manifest (`/ship/posts`, queue); other Ship pages keep waves only
- Deck waves on Crew Brand Brain (`/crew/clients/…`); removed atmosphere from Crew Deck list
- `AhoyScrollProgress` takes `trail` / `waves` props; Ship uses `ShipAtmosphere`

**How to try:** Manifest → grey trail. Map/Vault/Radar → waves, no trail. Crew client Brand Brain → waves.

---

## 0.6.68 — Wider trail into gutters

**Why:** Soft narrow path sat under the center column and disappeared.

**What shipped:**
- Larger swing amplitude so the slither reaches the side gutters

**How to try:** Hard-refresh `/ship` — grey trail should show left/right of the cards.

---

## 0.6.67 — Softer trail curves

**Why:** Even with fewer loops, the L↔R turns still looked sharp.

**What shipped:**
- Longer swing spacing (560 → 780) and smaller amplitude
- Gentler cubic handles so arcs ease instead of whipping through S-bends

**How to try:** Hard-refresh `/ship` — grey trail should feel like long soft waves.

---

## 0.6.66 — Fewer trail loops

**Why:** Slither swung L↔R too often.

**What shipped:**
- Doubled vertical swing spacing (280 → 560) so the path loops about half as often

**How to try:** Hard-refresh `/ship` — grey trail should take longer arcs between sides.

---

## 0.6.65 — Drop red tip and X

**Why:** Red marks cluttered the trail; grey slither is enough.

**What shipped:**
- Removed lantern tip circle and end X
- Grey dotted path still draws on scroll

**How to try:** Hard-refresh `/ship` — only the grey trail remains.

---

## 0.6.64 — Red tip behind content

**Why:** Red tip (and X) sat above panels; grey path was already behind.

**What shipped:**
- Tip + X drawn in the same behind-content SVG as the grey slither
- Removed the elevated marks layer

**How to try:** Hard-refresh `/ship` and scroll — red tip should duck under cards like the grey trail.

---

## 0.6.63 — Tip actually reaches the X

**Why:** Red tip stopped short — end coords and path terminus disagreed; progress rarely hit 100%.

**What shipped:**
- Path ends with an exact `L` onto the X point; tip + X both use `getPointAtLength(len)`
- Near page bottom (or past end Y), progress snaps to full length so the tip lands on the X
- Remeasure after the SVG path commits (double rAF)

**How to try:** Hard-refresh `/ship` and scroll to the bottom — red tip should meet the X, then become it.

---

## 0.6.62 — X below content, not on a post

**Why:** End mark was anchored on the last Manifest post.

**What shipped:**
- X / path end sits under `main` (clear of cards)
- Removed last-post trail end markers on Manifest

**How to try:** Hard-refresh `/ship/posts` and scroll to the bottom — X should sit in the space under the list.

---

## 0.6.61 — Keep red tip until the real end

**Why:** Tip vanished mid-scroll — hidden too early and drawn under opaque cards.

**What shipped:**
- Tip stays until ~98.5% path / page bottom (then X)
- Tip + X rendered in a higher layer above panels; grey path stays behind

**How to try:** Hard-refresh `/ship` and scroll — red tip should stay visible the whole way, then become the X at the end.

---

## 0.6.60 — Trail from first container to reachable X

**Why:** Path didn’t start on the first content block, and the tip often never reached the X.

**What shipped:**
- Path starts at the first `[data-ahoy-trail]` / Ship header container
- Ends on the last marked container; scroll-to-bottom snaps tip to the end so the X appears
- ShipHeader marked as trail start; Manifest last post (or empty state) marked as end

**How to try:** Hard-refresh `/ship` — grey trail begins on Treasure Map header; scroll to bottom for the red X.

---

## 0.6.59 — Subtler grey trail

**Why:** Trail still felt loud.

**What shipped:**
- Lower grey opacity, thinner/sparser dashes
- Smaller softer tip + quieter end X

**How to try:** Hard-refresh `/ship` — atmosphere-level trail.

---

## 0.6.58 — Grey trail, red tip, end X

**Why:** Wanted simple palette — grey path, red traveler, X only at the finish.

**What shipped:**
- Grey dotted slither; lantern-red tip only
- Simple crimson X fades in near the path end; tip hides then
- Still continuous down the page, behind content

**How to try:** Hard-refresh `/ship` — grey dots + red tip; scroll to the bottom for the X.

---

## 0.6.57 — Trail behind content again

**Why:** Lantern slither was sitting on top of cards.

**What shipped:**
- Dropped trail `z-index` under `.relative.z-10` so panels/nav stay on top
- Kept bright lantern dots + continuous downward slither

**How to try:** Hard-refresh `/ship` — crimson trail reads in the gutters, not over the cards.

---

## 0.6.56 — Clear lantern slither (early look)

**Why:** Downward slither was right, but grey Pirate Ship stroke was too faint — wanted the early bright crimson dots + tip.

**What shipped:**
- Lantern crimson dots + soft glow (not grey)
- Larger bright tip on the lead
- Trail floats above panels again (`z-index: 12`) so it stays readable
- Same continuous downward page slither

**How to try:** Hard-refresh `/ship` and scroll — obvious pink/crimson dotted trail snake-ing down with a glowing tip.

---

## 0.6.55 — Continuous slither down the page

**Why:** Viewport loop/lap wasn’t the ask — wanted the dotted trail to keep snake-ing downward as you scroll.

**What shipped:**
- Document-space serpentine generated to page height (more L↔R swings on longer pages)
- Ink + tip advance continuously down with scroll — no lap reset, no wrap to top
- Tip tracks ~mid-viewport so the slither rides with you down the page
- Trail stays behind content

**How to try:** Hard-refresh `/ship` or `/ship/posts` and scroll — grey dotted path should keep slithering downward without jumping back to the start.

---

## 0.6.54 — Continuous looping trail (no reset)

**Why:** Lap reset wiped the line and restarted at the top; wanted seamless circuits.

**What shipped:**
- Closed serpentine so the route is a real loop (no teleport at the seam)
- Moving wake + tip that wraps across the join instead of clearing
- Same constant scroll→lap speed; longer pages still mean more continuous laps

**How to try:** Hard-refresh `/ship/posts` and keep scrolling — dotted wake should ride around the circuit without jumping back empty.

---

## 0.6.53 — Trail loops at constant scroll speed

**Why:** Mapping 0–1 to full page height made long pages (Manifest) crawl the path; wanted more laps, same speed.

**What shipped:**
- Path progress uses fixed ~1.15 viewports per lap (`scrollY / loopPx % 1`)
- Longer pages complete more circuits; short pages still finish at least one pass while scrolling
- Top progress bar still tracks true page progress

**How to try:** Hard-refresh `/ship/posts` and scroll — dotted route should redraw/loop at a steady pace, not crawl.

---

## 0.6.52 — Fix Manifest crush from page-tall trail

**Why:** Trail SVG sized to document height — Manifest (~100+ posts) ballooned to ~26k px and felt broken.

**What shipped:**
- Dotted line is fixed-viewport again (never matches document height)
- Sits behind content so cards/tabs stay readable and clickable
- Manifest only runs AhoyReveal on the first 12 posts (rest render plain)

**How to try:** Hard-refresh `/ship/posts` — page should scroll normally; trail stays a light viewport overlay.

---

## 0.6.51 — Faithful Pirate Ship dotted line

**Why:** Floating crimson wake ≠ pirateship.com/features. Match their real model.

**What shipped:**
- Page-locked SVG (absolute over `.ahoy-trail-root`, scrolls with content)
- Brand stroke: width 8, dash `10 30`, round caps, grey foam color
- Mask trim reveal with scroll (dots stay in place — no sliding dashoffset on the dots)
- z-index 15 so it hovers above panels like their wrapper
- Removed tip/wake/X gimmicks

**How to try:** Hard-refresh `/ship` at top (little/no line) → scroll — grey dotted path grows down the page over the cards.

---

## 0.6.50 — Hovering Pirate Ship–style dotted trail

**Why:** Element-connector trail sat under cards and was effectively invisible. Want a moving hovering trail like Pirate Ship.

**What shipped:**
- Fixed full-viewport dotted serpentine that floats *above* content (`z-index: 25`)
- Only a moving wake (~40% of the route) is visible — travels with scroll; tip rides the lead
- Thick bright lantern dots + glow; X near the finish
- Waves stay as lower atmosphere

**How to try:** Hard-refresh `/ship` — crimson dotted trail should be obvious and slide along the path as you scroll.

---

## 0.6.49 — Reveal-only trail connecting page elements

**Why:** Whole route was visible at once; wanted ink that appears as you scroll, linking real UI.

**What shipped:**
- No ghost full path — only the scroll-revealed segment is drawn
- Path anchors to `[data-ahoy-trail]` (header → stat cards → CTA on `/ship`)
- Soft curves in document space; waypoints light as the tip reaches them; X at the end
- Waves stay as fixed atmosphere

**How to try:** Hard-refresh `/ship` at the top (almost no trail) → scroll down — crimson line grows between Treasure Map, the four cards, and the Manifest CTA.

---

## 0.6.48 — Full-screen draw-on-scroll trail

**Why:** Document-locked path looked unchanged on short `/ship` pages — faint, barely moved.

**What shipped:**
- Path is fixed full-viewport again (covers the screen, not a page slice)
- Soft full-bleed serpentine; scroll progress inks dashes + moves tip
- Short lead visible at top so the trail is obvious from the first paint
- X near finish; waves stay as fixed atmosphere

**How to try:** Hard-refresh `/ship` and scroll — crimson dashes grow across the screen with scroll; tip rides the lead.

---

## 0.6.47 — Document-space trail (fix broken lock)

**Why:** Fixed SVG + `translateY(-scrollY)` desynced from real page height — path looked stuck/broken.

**What shipped:**
- Path is `absolute inset-0` inside the relative page shell (scrolls with content, Pirate Ship–style)
- Dropped height/translate hack; waves/vignette stay fixed atmosphere
- ResizeObserver keeps draw progress in sync as content loads
- Softer full-bleed route (no stacked edge U-turns that read as a corner streak)
- Slightly stronger ghost + lantern stroke

**How to try:** Hard-refresh `/ship` — path spans the full page area and scrolls away with the cards while dashes ink in.

---

## 0.6.46 — Full-page path locked to scroll

**Why:** Path sat in a corner of the viewport instead of riding the real page scroll.

**What shipped:**
- Path SVG height = document height; `translateY(-scrollY)` locks it to the page
- Broad full-width serpentine; thicker draw stroke
- Tip + end X still driven by scroll progress

**How to try:** Hard-refresh `/ship` — dashed line spans the page and draws as you scroll the content.

---

## 0.6.45 — Pirate Ship–style draw-on-scroll path

**Why:** Floating ribbon ≠ Pirate Ship. Want the dashed path to *draw* as you scroll.

**What shipped:**
- Broad serpentine path revealed via `stroke-dasharray` from scroll progress
- Tip traveler on the leading edge; X only near finish
- Removed viewport-sliding ribbon

**How to try:** Hard-refresh `/ship` — path grows downward with scroll; undoes on scroll up.

---

## 0.6.44 — Scroll-following ribbon

**Why:** Static map path felt wrong — the trail should ride with scroll.

**What shipped:**
- Removed fixed full-route spine
- Wide L→R dotted ribbon that moves down the viewport with scroll
- Trailing side fades; lead stays bright; dashes crawl with progress
- X still only near the finish

**How to try:** Hard-refresh `/ship` and scroll — the ribbon travels with you.

---

## 0.6.43 — Broader, thicker trail

**Why:** Path felt narrow; visible dots needed more weight.

**What shipped:**
- Wider left↔right serpentine (near full deck width)
- Thicker visible crimson dots (`strokeWidth` 3.25)
- Slightly wider trail SVG inset

**How to try:** Hard-refresh `/ship` — broader swings, heavier dotted stroke.

---

## 0.6.42 — X only at the finish

**Why:** Treasure mark should stay hidden until the Captain reaches the end.

**What shipped:**
- X fades in only after ~92% scroll progress

**How to try:** Hard-refresh `/ship` and scroll to the bottom — X appears at the trail end.

---

## 0.6.41 — Visible trail X

**Why:** End X was easy to miss (low, soft, under vignette).

**What shipped:**
- Path ends at fixed center mark `(600, 400)`
- Larger crimson X with deck halo
- Trail SVG above waves/vignette (`z-index: 2`)

**How to try:** Hard-refresh `/ship` — X should sit mid-screen at the trail end.

---

## 0.6.40 — Align traveler to start/end

**Why:** Progress inset left the scroll dot short of the path head and the X.

**What shipped:**
- Full 0→1 scroll mapping along the path
- Snap traveler to exact start/end points at the extremes

**How to try:** Hard-refresh `/ship` — top of page sits on the trail head; bottom sits on the X.

---

## 0.6.39 — Keep trail X in frame

**Why:** End X sat too low and clipped into the wave area.

**What shipped:**
- Shortened path; finish ~mid viewport
- Extra bottom inset on the trail SVG box

**How to try:** Hard-refresh `/ship` and scroll to the bottom — X stays on screen.

---

## 0.6.38 — Trail end X only

**Why:** Start port mark was unnecessary; keep the treasure X.

**What shipped:**
- Removed start circle
- Kept crimson **X** at trail end

**How to try:** Hard-refresh `/ship` — X at the finish only.

---

## 0.6.37 — Trail start + end marks

**Why:** Voyage needed a clear beginning and treasure end.

**What shipped:**
- Start: open port circle at path head
- End: crimson **X** at path tail
- Faint full dotted spine so the route reads start→end

**How to try:** Hard-refresh `/ship` — circle at the start, X at the finish.

---

## 0.6.36 — Trail stays in frame

**Why:** Marker/trail clipped under the nav at the start and into the waves at the end.

**What shipped:**
- Path inset inside a safe frame (clear of header + wave strip)
- SVG `meet` + padded layout box
- Scroll progress eased so start/end sit slightly on-path

**How to try:** Hard-refresh `/ship` — first and last scroll positions keep the trail visible.

---

## 0.6.35 — Softer, less clustered trail

**Why:** Turns felt pointy; dots/path reads were too bunched.

**What shipped:**
- Wide soft U-turns (serpentine L→R with roomy vertical gaps)
- Airier dash spacing (`2 22`)
- Shorter visible window so fewer dots on screen at once

**How to try:** Hard-refresh `/ship` — open curves, sparse crimson dots.

---

## 0.6.34 — Cleaner trail

**Why:** Trail overlay felt messy (too many strokes / zigzags).

**What shipped:**
- One soft S-curve path, single crimson dotted stroke
- Slimmer scroll window + tiny marker
- Two quieter wave layers (dropped the third)

**How to try:** Hard-refresh `/ship` — calmer dotted trail over soft waves.

---

## 0.6.33 — Single serpentine dotted trail

**Why:** Rows of lines were wrong — needed one continuous L→R trail that travels down.

**What shipped:**
- One serpentine dotted path (left→right legs, descending)
- Scroll window: trail behind clears, lead ahead pops
- Soft marker on the path; waves kept

**How to try:** Hard-refresh `/ship` and scroll — follow the single winding dotted trail.

---

## 0.6.32 — L→R bands that pop while traveling down

**Why:** Wanted left-to-right dotted lines that travel downward and pop as they enter.

**What shipped:**
- Stacked horizontal dotted bands (alternating L→R / R→L)
- Scroll focus moves top→bottom: trailing bands fade out, leading bands scale/pop in
- Crimson accent on the active band + soft pip
- Waves kept

**How to try:** Hard-refresh `/ship` and scroll — each L→R row pops as you reach it, then clears behind.

---

## 0.6.31 — Subtle vertical trail window

**Why:** Trail should run top→bottom; past dots vanish, ahead dots appear; overall quieter.

**What shipped:**
- Vertical dotted path (center, slight curve)
- Scroll-linked mask: trailing fade-out, leading fade-in
- Softer marker + quieter waves
- Side trails removed

**How to try:** Hard-refresh `/ship` and scroll — dots behind you clear; dots ahead open up.

---

## 0.6.30 — Dotted trail follows scroll

**Why:** Lines were sliding away; they should stay on screen and track the Captain.

**What shipped:**
- Dotted trails fixed to the viewport (no parallax fly-off)
- Crimson route draws with scroll progress
- Marker (X-dot) rides the path as you scroll
- Waves kept rolling at the keel

**How to try:** Hard-refresh `/ship` and scroll — the crimson spot moves along the trail with you.

---

## 0.6.29 — Waves + scroll dotted trails

**Why:** Wanted the sine waves back, with dotted trails that clearly move on scroll.

**What shipped:**
- Restored monochrome/crimson wave tracks at the keel
- Three visible dotted voyage paths (ink + crimson) with parallax + dash crawl
- Small crimson X; map grid/islands cartouche removed for clarity

**How to try:** Hard-refresh `/ship` and scroll — dotted lines slide; waves keep rolling.

---

## 0.6.28 — Map lines scroll with you

**Why:** Treasure map felt static; lines should slide as the Captain scrolls.

**What shipped:**
- Parallax layers: grid (fastest), route, islands, X/cartouche (slowest)
- Route dash offset tied to scroll position
- Extended grid so lines keep flowing without empty edges

**How to try:** Hard-refresh `/ship` and scroll — latitude/longitude lines drift under the deck.

---

## 0.6.27 — Treasure map overlay

**Why:** Wanted a treasure-map theme behind the deck, not sail/waves chrome.

**What shipped:**
- Full-bleed map overlay: grid, torn border, islands, palms, mountains
- Crimson dashed voyage route + pulsing **X**
- Small cartouche legend; ink grain; vignette keeps UI readable
- Removed wave tracks / sail / anchor

**How to try:** Hard-refresh `/ship` — chart sits behind Treasure Map content.

---

## 0.6.26 — Sail + anchor overlay marks

**Why:** Floating compass rose and glow ball felt wrong for the deck.

**What shipped:**
- Removed compass + lantern ball
- Soft sail/pennant (gentle sway) and faint anchor (soft bob)
- Chart latitude lines kept

**How to try:** Hard-refresh `/ship` — sail starboard, anchor port, over the waves.

---

## 0.6.25 — Monochrome wave colors

**Why:** Teal / crimson / indigo wave bands fought the B/W deck.

**What shipped:**
- Wave fills + most strokes use `ahoy-fg` at low opacity
- One pennant crimson crest as the accent line
- Vignette stays neutral (no kelp wash)

**How to try:** Hard-refresh `/ship` — waves should read ink/foam + one crimson line.

---

## 0.6.24 — Real sine waves, no clipping

**Why:** Overlay blobs didn’t read as waves; edges looked cut off.

**What shipped:**
- Proper cubic sine wave strokes + soft fills (3 layers)
- Seamless horizontal loop (`translateX(-50%)` on a 2× tile)
- Waves live in a bottom strip; chart rose kept clear of the crop

**How to try:** Hard-refresh `/ship` — continuous rolling sine lines at the keel.

---

## 0.6.23 — Stronger overlay motion

**Why:** Ambient overlay was too faint to notice.

**What shipped:**
- Higher tide/rose/glow opacity; wider wave travel
- Faster loops (~18–28s tides, 72s rose, 6–8s glow)
- Lighter vignette so the chart reads through

**How to try:** Hard-refresh `/ship` — sea bands and rose should be obvious behind content.

---

## 0.6.22 — Overlay ambient motion

**Why:** Background chart was still; wanted life in the overlay without crowding UI.

**What shipped:**
- Tide bands slowly drift (staggered, alternate)
- Compass rose turns over ~3 min
- Latitude lines + lantern glow soft breathe
- Still behind content; `prefers-reduced-motion` kills loops

**How to try:** Hard-refresh `/ship` and watch the background sea/chart, not the cards.

---

## 0.6.21 — Quieter pirate atmosphere

**Why:** Ship mark + rolling sea + yawing cards were too distracting vs. the work.

**What shipped:**
- Removed voyage ship and bottom wave strip
- Soft chart/sea **background overlay** + vignette (gentle parallax)
- Thin progress line only; reveals reduced to a soft lift
- Content stays above overlay (`z-10`)

**How to try:** Hard-refresh `/ship` — atmosphere sits behind the deck, not on it.

---

## 0.6.20 — Pirate scroll motions

**Why:** Plain fade-up felt generic; scroll should feel like sailing.

**What shipped:**
- Reveal variants: `sail` (port fill), `heave` (bilge sway), `drop` (anchor)
- Voyage rope + tiny ship mark tracking scroll at the top
- Rolling sea strip at the keel (translateX with scroll)
- Wired across Ship + Crew; still transform/opacity only

**How to try:** Hard-refresh `/ship` and scroll — ship rides the rope; cards yaw in.

---

## 0.6.19 — Scroll animations

**Why:** Website feel — content should rise into view as you sail down the page.

**What shipped:**
- `AhoyReveal` — IntersectionObserver fade/rise (transform + opacity only; once)
- Staggered cards/list rows on Ship Map, Manifest, Vault, Radar + Crew Deck
- `AhoyScrollProgress` — thin crimson scaleX bar at the top
- Honors `prefers-reduced-motion`

**How to try:** Hard-refresh `/ship`, scroll the Map cards / open Manifest.

---

## 0.6.18 — Fix dual-server nav break

**Why:** Two `next dev` instances (3000 + 3001) left JS/CSS out of sync — top links rendered as one glued string.

**What shipped:**
- Nav spacing/active underline via Tailwind on the component (no fragile custom class dependency)
- Wider gaps between Map / Manifest / Vault / Radar
- Kill duplicate servers; run a single web dev process

**How to try:** Use only `http://localhost:3000/ship` after one `npm run dev` in `apps/web`.

---

## 0.6.17 — Top nav polish

**Why:** First top-nav pass still felt like a relocated app bar (icon pills); layout also broke when CSS lagged HMR.

**What shipped:**
- Classic site header: logo · text links · theme (Tailwind for structure)
- Active = crimson underline, not filled pills; dropped per-link icons
- Solid sticky bar (no frosted wrap)

**How to try:** Hard-refresh `/ship` — single-row header with Map / Manifest / Vault / Radar.

---

## 0.6.16 — Top site navigation

**Why:** Bottom tab bar read as an app; this is a website — primary nav belongs at the top.

**What shipped:**
- Ship chrome: sticky top header (logo + horizontal links + theme toggle)
- Removed bottom-fixed nav and `pb-24` spacer
- Theme dock hidden on `/ship` (toggle lives in the header)

**How to try:** Open `/ship` — nav is along the top; hover links for lift.

---

## 0.6.15 — Bigger returns + hover motion

**Why:** Return paths were easy to miss; controls needed clearer hover feedback without GPU thrash.

**What shipped:**
- `AhoyBackLink` — 48px+ hit target, copper edge, arrow slides on hover
- Wired on Crew client detail, sign-in → Home, Logbook → Manifest
- Button/ghost/tab/logo hover via transform only; gated Sign-in CTAs use `ahoy-btn`
- `prefers-reduced-motion` kills hover transforms

**How to try:** Open a Crew client → big “Crew Deck” return; hover buttons on Ship.

---

## 0.6.14 — Faster first load

**Why:** Dual Google fonts + eager ROI breakdown made first paint feel slow.

**What shipped:**
- Single font (Atkinson only; display uses same face via size/weight)
- `display: swap` + font fallback adjust
- Route `loading.tsx` shells
- Treasure Map: ROI summary first; breakdown fetch only when opened

**How to try:** Hard-refresh `/ship` — Map should paint sooner; open revenue for breakdown.

---

## 0.6.13 — Align type system

**Why:** Mixed Tailwind `text-sm` / `font-semibold` / mono fought Fraunces + Atkinson scale.

**What shipped:**
- Roles only: `ahoy-brand`/`logo-word`, `title`, `title-sm`, `stat`, `prose`, `muted`, `label`, `strong`, `nav-label`
- Stripped stray size/weight utilities from Ship/Crew/auth; tables/inputs/tabs inherit scale

**How to try:** Hard-refresh — headings should share Fraunces sizes; body/UI share Atkinson.

---

## 0.6.12 — A-hoy logo

**Why:** Brand needed a real mark, not only loose pirate icons.

**What shipped:**
- SVG logo: sail-as-**A** + hull + pennant (`AhoyLogo` / `AhoyMark`)
- Wired on landing, sign-in, Ship nav; favicon `app/icon.svg`
- Raster mark also at `apps/web/public/ahoy-logo-mark.jpg` (generated asset)

**How to try:** `/` hero logo; favicon in the browser tab; nav mark on Ship.

---

## 0.6.11 — Type that pops + stays readable

**Why:** Need stronger hierarchy without losing body clarity.

**What shipped:**
- Display: Fraunces (brand + titles) with clamp() scale
- Body/UI: Atkinson Hyperlegible at 18px+; buttons bold 700
- Clearer size steps: brand / title / title-sm / body / kicker

**How to try:** Hard-refresh `/` — big soft display headlines, plain readable body.

---

## 0.6.10 — Atkinson Hyperlegible

**Why:** Source Sans still felt wrong; need maximum on-screen clarity.

**What shipped:**
- UI face → Atkinson Hyperlegible (400/700)
- Base size 18px; slightly roomier title/prose line-height

**How to try:** Hard-refresh. If you still hate it, say whether you want serif, rounded, or mono-ish next.

---

## 0.6.9 — Readable UI type

**Why:** EB Garamond (esp. italic brand/kickers) was hard to scan.

**What shipped:**
- Single face: Source Sans 3 for brand, titles, and body
- Dropped italic display; tighter sans titles / uppercase kickers

**How to try:** Hard-refresh — type should feel clearer everywhere.

---

## 0.6.8 — Pennant accent (drop orange)

**Why:** Lantern orange read as generic warm CTA; wanted a sharper pirate signal.

**What shipped:**
- Primary accent → pennant crimson (`--ahoy-lantern`)
- Secondary fittings → indigo (`--ahoy-copper`); links stay kelp/teal

**How to try:** Hard-refresh — buttons, top stripe, active nav/tabs should be crimson, not orange.

---

## 0.6.7 — Reviews theme surfaces

**Why:** Reputation Radar draft boxes used always-black `--ahoy-void` + hardcoded emerald/red, so Night/Day watch barely showed.

**What shipped:**
- Reviews use `ahoy-inset`, lantern stars, `ahoy-success` / `ahoy-error`
- Same message/inset fix on Manifest placeholders

**How to try:** Radar → toggle Day/Night — cards, draft reply, stars should flip with the deck.

---

## 0.6.6 — In-app Day / Night watch toggle

**Why:** Demo needs explicit light/dark without relying on OS settings alone.

**What shipped:**
- `data-theme` on `<html>` + `localStorage` (`ahoy-theme`)
- Boot script to prevent flash; `ThemeProvider` + **Day watch / Night watch** dock (all pages)
- CSS keyed off `html[data-theme="light"|"dark"]` (B/W deck, pirate accents)

**How to try:** Top-right **Night watch** / **Day watch** — persists across refresh.

---

## 0.6.5 — B/W deck + pirate chrome

**Why:** Wanted a simple black/white page (system light/dark) with pirate limited to accents, assets, and light motion.

**What shipped:**
- `prefers-color-scheme`: `#fff` / `#000` page + matching panels
- Pirate kept on: lantern CTAs, copper kickers/marks, kelp links, lantern top stripe, SVG marks
- One-shot rise + rule glow only (`prefers-reduced-motion` off)

**How to try:** Toggle OS light/dark → hard-refresh. Background flips B/W; accents stay pirate.

---

## 0.6.4 — Chart room daylight

**Why:** Privateer cabin was distinctive but too dark to live in.

**What shipped:**
- Light salt-stained parchment deck + sailcloth panels; ink text
- Kept lantern CTAs, copper fittings, kelp links, EB Garamond
- Nav: light sailcloth with mahogany active state

**How to try:** Hard-refresh `/` — bright chart paper, still warm privateer (not navy SaaS).

---

## 0.6.3 — Privateer cabin (less generic)

**Why:** Cool navy + brass read as stock “dark pirate SaaS.” Needed a warmer, chart-room identity that stays sloop-fast.

**What shipped:**
- Palette: tar deck, mahogany plank, bone text, lantern amber CTAs, copper fittings, kelp links, signal red
- Display font: EB Garamond (italic brand/kickers) instead of Cinzel
- Kickers copper italic (not uppercase tracking-heavy navy labels)

**How to try:** Hard-refresh `/` — warm brown hold, lantern buttons, bone type (not blue-black + gold).

---

## 0.6.2 — Night hull palette

**Why:** Light deck read as generic SaaS; needed a darker pirate hold without bringing back GPU-heavy effects.

**What shipped:**
- Palette: void/hull/deck/plank + foam text, bright brass CTAs, sea links ([apps/web/src/app/globals.css](../apps/web/src/app/globals.css))
- Brass waterline stripe; brass primary buttons; dark nav with brass active
- Replaced leftover light `slate-*` utilities on Ship/Crew surfaces

**How to try:** Hard-refresh `/` and `/ship` — should feel below-decks dark with brass fittings.

---

## 0.6.1 — Pirate SVG marks

**Why:** Theme needed recognizable pirate assets without image weight or GPU effects.

**What shipped:**
- Inline SVG set: wheel, compass, scroll, chest, spyglass, anchor, sloop, coins ([apps/web/src/components/pirate/Icons.tsx](../apps/web/src/components/pirate/Icons.tsx))
- Ship nav icons; page headers via `ShipHeader`; landing + sign-in marks
- Stroke/`currentColor` only — no raster, blur, or animation

**How to try:** `/` (sloop/wheel/anchor) → Ship bottom nav icons → Treasure Map / Manifest / Vault / Radar titles.

---

## 0.6.0 — Sloop theme (pirate + fast)

**Why:** Wanted a clearer pirate read without the galleon-weight CSS that slowed the machine.

**What shipped:**
- Sloop palette: hull ink, sea waterline, cool deck, sail panels, brass fittings — **solid fills only**
- Body: flat deck + 5px hull top stripe (no gradients/blur/keyframes)
- Panels: sail white + inset brass nail edge
- Primary buttons: hull ink; jib-sail CSS triangle on brand marks
- Nav: solid sail bar with hull active state
- Still 2 Google fonts / minimal weights

**How to try:** Hard-refresh `/` — should feel snappy; look for hull stripe, brass panel edge, jib on **A-hoy**.

---

## 0.5.2 — Theme perf (whole-PC load)

**Why:** Layered body gradients + motion still taxed GPU; three Google font families with many weights inflated Next/Turbopack work (~1GB `next dev`).

**What shipped:**
- Flat mist background only (no radial stacks, no keyframes)
- Dropped Source Code Pro; Cinzel/Source Sans limited to needed weights
- Rise animation classes are no-ops

**How to try:** Hard-refresh (Ctrl+Shift+R). If the machine is still hot, restart `npm run dev` in `apps/web` — the old Turbopack process was ~1GB RAM.

---

## 0.5.1 — Theme perf (kill scroll jank)

**Why:** Infinite body `background-position` animation + full-viewport chart grid + `backdrop-filter` on every panel forced constant paint and felt laggy.

**What shipped:**
- Removed `ahoy-swell` infinite animation and fixed chart-grid overlay
- Solid panels/nav (no backdrop blur); simpler button hover (no `filter`/`transform`)
- `prefers-reduced-motion` disables rise animations

**How to try:** Hard-refresh `/ship` — scroll and tab switches should feel normal again.

---

## 0.5.0 — Pirate / nautical UX theme

**Why:** Product metaphor (Ship, Crew, Treasure Map) was verbal only — UI still looked like generic SaaS slate/sky.

**What shipped:**
- Theme tokens: ink / sea / foam / brass; chart-grid + swell atmosphere ([apps/web/src/app/globals.css](../apps/web/src/app/globals.css))
- Fonts: Cinzel (display/brand) + Source Sans 3 (UI) + Source Code Pro
- Shared chrome: `.ahoy-brand`, `.ahoy-title`, `.ahoy-panel`, `.ahoy-btn`, `.ahoy-tab`, rise/swell motion
- Landing brand-first **A-hoy**; Ship nav Map / Manifest / Vault / Radar
- Copy/surfaces aligned across Ship, Crew, sign-in

**How to try:** Open `/` then Captain `/ship` and Crew `/crew` — sea mist background, engraved titles, brass rules.

**Related:** post-C polish (not Milestone D)

---

## 0.4.0 — Test matrix + A↔B↔C integration

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

## 0.3.0 — Ship Posts + Queue merge

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

## 0.2.0 — Crew UX polish (type, media upload, Posts tabs)

**Why:** Make Crew Deck readable and match the staged draft → release → approved mental model.

**What shipped:**
- Geist on body, larger base type, `.ahoy-prose` / `.ahoy-muted` on Crew + Ship surfaces
- Crew media: **Upload photo** + thumbnails (below Brand Brain)
- Crew **Posts** tabs: Drafts / Awaiting Captain / Approved (replaces mixed queue table)

**How to try:** Crew `+15551234002` → client page → Brand Brain → Media → Generate drafts → Posts tabs → Release.

**Related:** [milestone_b.md](./milestone_b.md)

---

## 0.1.0 — Approval refill path documented + test

**Why:** Captains need a clear path after approving empties the awaiting list.

**What shipped:**
- Docs for generate → release refill after approve
- `test_approve_leaves_queue_and_refill_via_generate_release` (`milestone_b`)

**How to try:** Approve all awaiting posts as Captain → Crew Generate + Release → posts reappear under Awaiting you.

**Related:** [milestone_b.md](./milestone_b.md)
