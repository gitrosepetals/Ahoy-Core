# Milestone D — Pilot hardening + Phase 1 PRD gaps (build log)

**Status:** Done (code, 1.0.0) — pilot rollout pending  
**Goal:** Close every Phase 1 gap against the PRD (`CL-01`, `CL-02`, `CL-05`, `AG-01`, `AG-03`, Stories 1.1 / 1.2 / 2.1) and harden for the 5–10 client pilot.

Tracks [technical_implementation_plan.md](./technical_implementation_plan.md) § Milestone D. Releases are logged in [iterations.md](./iterations.md); defects in [bug_log.md](./bug_log.md).

**Why this milestone grew:** A PRD audit on 2026-11-01 found Milestones A–C ran end-to-end on seed data and stubs (no publishing, notifications log-only, no live data sources, no billing). The original D list (Stripe, Ayrshare, Twilio call tracking, observability) is kept; audit gaps are added as D-items so they are tracked in one place.

---

## Checklist

| # | Item | PRD | Release | Status |
|---|---|---|---|---|
| D1 | ROI correctness: POS vs estimate per client, billing period, qualified calls | CL-01 / 2.1 | 0.7.0 | Done |
| D2 | Brand Brain: pricing + seasonal offers; full context injected in every prompt | AG-01 / 1.2 | 0.7.0 | Done |
| D3 | Campaign generator: all channels, per-channel variations, local SEO + hashtags, AI asset tags | AG-03 | 0.7.0 | Done |
| D4 | Crew "Needs crew" revisions view + manual caption edit | 1.2 | 0.7.0 | Done |
| D5 | Real notifications (Twilio SMS async, push dispatch hook), queue-ready SMS deep link with 48h token | CL-02 / 1.1 | 0.8.0 | Done |
| D6 | Queue expiry + 48h-before reminder; low-star alert wired | CL-02 / CL-05 | 0.8.0 | Done |
| D7 | Background job runner (publish, reminders, delayed replies, nightly rollup) | — | 0.9.0 | Done |
| D8 | Ayrshare publish job → `published` + `published_external_id` | CL-02 | 0.9.0 | Done |
| D9 | Twilio call tracking + form leads → `lead_events` → nightly rollup; itemized breakdown; Detailed View | CL-01 / 2.1 | 0.10.0 | Done |
| D10 | Review ingestion (GBP) + post replies; 24h auto-reply delay | CL-05 | 0.11.0 | Done |
| D11 | Stripe subscription ↔ `subscription_tier` | — | 0.13.0 | Done |
| D12 | Ship client switcher; PWA manifest + service worker; voice-note edit requests | CL-02 | 0.12.0 | Done |
| D13 | Audit log of status transitions; Sentry hook | — | 0.15.0 | Done |
| D15 | Terminology sweep: Captain / Ship / Crew in all user-facing copy | — | 0.14.0 | Done |
| D14 | Pilot rollout (5–10 SMBs) + PRD §7 KPIs | §7 | 1.0.0 | KPI tooling done; rollout pending |

---

## Phase 1 PRD coverage (1.0.0)

| PRD item | Status | Where |
|---|---|---|
| CL-01 Treasure Map | Done — real calls (>60s) + forms, POS-or-estimate per client, billing period, itemized breakdown with recordings, Detailed View. Ads APIs = Phase 3 (Crew enters spend). | 0.7, 0.10, 0.11 |
| CL-02 Approval queue | Done — feed/list, swipe + approve, approve all, text + voice edits, swap media, 48h deep link, expiry + 48h reminder, auto-publish (email/SMS sent manually). | 0.8, 0.9, 0.12 |
| CL-05 Reputation Radar | Done — Google + Facebook (reply), Yelp (read-only, copy reply), auto-reply with per-client delay, low-star alert + one-click approve. | 0.8, 0.11 |
| AG-01 Brand Brain | Done — all fields, full context in every prompt (no retrieval needed with one profile per client). | 0.7 |
| AG-03 Campaign generator | Done — all channels, per-channel variations, local SEO + hashtags, AI asset tags. | 0.7 |
| Stories 1.1 / 1.2 / 2.1 | Done | 0.7–0.12 |
| §4 Stripe, PWA, push | Done | 0.12, 0.13 |
| §7 KPIs | Measured in-app: time-to-approve, Captain activity, churn. Crew minutes / gross margin: outside the app. | 1.0 |

**Known follow-ups (not blocking the pilot):** email/SMS campaign sender for `email_blast` / `sms_promo`; media + voice notes on Blob/S3 with signed URLs; native Capacitor builds (push token registration on device); frontend automated tests.

---

## Design decisions

- **POS vs estimate is per client** (`clients.pos_provider` set ⇒ POS). PRD: "If POS integration is active". Fixes BUG-001. (0.7.0)
- **Billing period** = monthly cycle from `clients.billing_anchor_day` (1–28; becomes Stripe's anchor day in 0.12.0). `GET /roi` with no `days` uses it; `?days=N` remains a rolling override. (0.7.0)
- **"Calls over 60s"** is enforced where calls are counted (lead_events → rollup, 0.10.0), so `daily_roi_metrics.tracked_calls_count` means *qualified* calls; the API exposes `qualified_call_min_seconds`. (0.7.0)
- **No vector retrieval yet.** Each client has exactly one Brand Brain row, so the whole profile is injected into every prompt (`BrandContext.as_prompt`) — retrieval would return the same single row. The embedding is kept for future per-asset / past-post similarity search. (0.7.0)
- **Fan-out batches** (`fan_out: true`): each slot produces one formatted variation per channel sharing asset + time and a `batch_id`; capped at 60 posts. Default stays round-robin for API compatibility. (0.7.0)
- **Channel formatting** lives in `llm.CHANNEL_RULES` (hashtags only on IG/TikTok/FB; GBP plain text; email gets Subject/Preview). (0.7.0)

- **Push first, SMS fallback, log in dev.** `notify._notify_owner` tries FCM (HTTP v1, service-account JWT) on every enabled device token; dead tokens are disabled; if no push succeeds it sends a Twilio SMS. SMS is live only when Twilio is configured **and** `AUTH_DEV_MODE=false`. Every attempt is a `notifications` row. (0.8.0)
- **Story 1.1 deep link:** every SMS notification carries a single-use magic link (TTL `NOTIFY_LINK_TTL_HOURS`=48) whose `redirect_path` is the screen to open (`/ship/posts?tab=pending`, `/ship/reviews`). Sign-in links typed on the sign-in page stay at 30 min. Single-use + 48h session JWT keeps a forwarded SMS from being a permanent key. (0.8.0)
- **Queue expiry = the post's publish time.** An unapproved post can't publish, so at `scheduled_publish_at` it becomes `expired` and lands in Crew's **Expired** tab; Crew reschedules (new time required) to send it back. Reminder: one message per client for posts expiring within `QUEUE_REMINDER_HOURS_BEFORE`=48h, once per post (`reminder_sent_at`), skipped for posts released in the last hour. (0.8.0)
- **Low-star alert fires once** per review (`reviews.alerted_at`) the first time a 1–3★ review is drafted and waiting on the Captain; message includes the start of the drafted reply. (0.8.0)
- **Worker = plain asyncio loop, no new infra.** `python -m app.worker` (or `EMBEDDED_WORKER=true` inside the API). Each job runs in its own transaction behind `pg_try_advisory_xact_lock`, so extra workers are safe; Redis/arq not needed at pilot scale (5-10 clients). `--once` runs every job once (cron/smoke test). (0.9.0)
- **Publish at the post's time, from our side.** The worker publishes `approved` posts whose `scheduled_publish_at` has passed (not Ayrshare's scheduler), so un-approve/expiry rules stay in one place. Batches of 50, `FOR UPDATE SKIP LOCKED`. (0.9.0)
- **Ayrshare per-client profile keys** are stored encrypted (Fernet, key derived from `CREDENTIALS_ENCRYPTION_KEY`) in `integration_credentials`; never returned by the API. Without `AYRSHARE_API_KEY` publishing runs in dev mode (fake `dev-…` id). (0.9.0)
- **Failures:** up to `PUBLISH_MAX_ATTEMPTS`=3 tries (one per worker minute), then `publish_failed` and Crew can Retry or Mark sent. **Email/SMS** are not Ayrshare channels: flagged `needs_manual_publish` for Crew until an email/SMS provider is chosen (follow-up). TikTok without media fails fast (TikTok requires media). (0.9.0)
- **Media must be publicly reachable** for Ayrshare: local `uploads/` URLs (localhost) won't work in production — set `PUBLIC_API_BASE_URL` to a public host or move uploads to Blob/S3 (open item). (0.9.0)
- **Call tracking = Twilio forwarding.** Each client's tracking number has Voice URL `POST /webhooks/twilio/voice`; we answer with TwiML `<Dial>` to `clients.forward_to_number`, and the Dial `action` callback stores talk time (`DialCallDuration`). Qualification (>= 60s) uses talk time, applied in the rollup. Events are idempotent per `CallSid` (unique index), so Twilio retries never double-count. (0.10.0)
- **Recording consent:** when `record_calls` is on (default) the caller first hears "This call may be recorded…" — Illinois (the pilot market) is an all-party-consent state. Recordings stay in Twilio; the API proxies playback with account auth (`GET /clients/{id}/leads/{event}/recording`). (0.10.0)
- **Twilio signatures** (`X-Twilio-Signature`, HMAC-SHA1 over `PUBLIC_API_BASE_URL` + path + sorted params) are enforced whenever a Twilio auth token is set and `AUTH_DEV_MODE=false`. `PUBLIC_API_BASE_URL` must be the exact public URL Twilio calls. (0.10.0)
- **Form leads:** public `POST /webhooks/forms/{lead_form_key}` (per-client random key, generated on first Crew settings view). Accepts a plain HTML form (no JS/CORS needed; `_redirect` → 303 to a thank-you page) or JSON (Zapier). `_gotcha` honeypot; email or phone required. (0.10.0)
- **Rollup is hourly and idempotent** (today + 2 prior local days, client `timezone`), recounting calls / forms / directions / new reviews into `daily_roi_metrics`. Days without any events are left untouched so Crew-entered or seeded rows survive. (0.10.0)
- **Ad spend / impressions / clicks are Crew-entered for now** (`PUT /clients/{id}/roi/manual`, concierge MVP). Meta/Google Ads APIs are Phase 3 per the PRD rollout; GBP impressions/directions come with the GBP integration. The Ship's **Detailed View** (impressions, clicks, CTR, directions, cost per lead) is hidden by default and remembered per device. (0.10.0)
- **Google first, all three supported.** Google Business Profile: OAuth (the Captain signs in once; refresh token encrypted), v4 reviews + reply API, location picker via Account Management / Business Information APIs. Facebook: Page ratings via Graph API, reply as a comment on the rating's story (Page token entered by Crew). Yelp: Fusion API is read-only (3 latest excerpts, no reply endpoint) → replies are copied by hand from the Ship. (0.11.0)
- **Auto-reply delay is per client** (`auto_reply_delay_hours`, default 24, 0–72). New 4–5★ reviews get a drafted reply in status `scheduled` with `reply_due_at`; the worker posts it then (`auto_sent` = actually posted). The Captain can edit, Send now, or Don't reply. 1–3★ wait for the Captain (alert from 0.8.0); approve posts immediately with worker retry (3 attempts). (0.11.0)
- **Reviews the Captain already answered** on the platform are imported as `skipped` with their existing reply — we never double-reply. (0.11.0)
- **GBP Performance owns impressions / clicks / directions** (6-hourly job, 10-day lookback for Google's reporting lag); the lead rollup no longer writes `gbp_direction_requests`. (0.11.0)
- **Local dev:** replies for providers that aren't connected 'post' in dev mode when `ENVIRONMENT=development` (flow completes); in any other environment they fail with "not connected". (0.11.0)
- **0.12 was split into 0.12.0 (Ship: switcher, voice notes, PWA/push), 0.13.0 (Stripe) and 0.14.0 (audit log + Sentry)** so each release stays reviewable. (0.12.0)
- **Active business is a per-device choice** (`localStorage`), validated against `/auth/me` on every load; the switcher only appears for Captains with 2+ businesses and reloads the page to keep every screen consistent. (0.12.0)
- **Voice notes** (Story 1.2): recorded in the browser (MediaRecorder, max 30s, ≤2 MB), stored under `uploads/{client}/voice/`, transcribed with Whisper, then run through the same AI-rewrite loop as text. If transcription fails the post goes to Crew's Needs crew tab with the audio player. Notes are served like media (unguessable URL, no auth) — acceptable for the pilot; move to signed Blob/S3 URLs with the media store. (0.12.0)
- **PWA without offline caching:** manifest + service worker make the Ship installable and receive FCM web push; no offline cache because stale approval data is worse than an error. Firebase web config is passed to the service worker in its registration URL (workers can't read env vars). (0.12.0)
- **Swipe right to approve** (Story 1.1) on touch devices in Feed view (≥90px horizontal); approving no longer reloads the whole Manifest — the card updates in place from the API response. (0.12.0)
- **Stripe via REST, webhooks are the source of truth.** Checkout (mode subscription) creates/reuses one Stripe customer per client; `customer.subscription.*` webhooks set `tier` (from the price id), `subscription_status`, `current_period_end` and `billing_anchor_day` (Stripe's cycle anchor day, capped at 28 — the Treasure Map's billing period now follows real billing). Signature checked (`Stripe-Signature`, 5-min tolerance); events stored in `stripe_events` so retries apply once. (0.13.0)
- **Ad-spend pass-through** = Crew-created pending invoice items on the client's next Stripe invoice (PRD §4). Kept separate from the Treasure Map's ad-spend metric (Crew enters both) because billing date ≠ spend date. (0.13.0)
- **Who can do what:** Captain and Crew can open Checkout and the customer portal (card, invoices, cancel); only Crew can bill ad spend. Billing UI hides itself when Stripe isn't configured. (0.13.0)
- **Terminology sweep inserted as 0.14.0** at the Captain's request (Captain = business owner, Ship = the app, Crew = A-hoy team); audit log + Sentry move to 0.15.0. (0.13.0)
- **Vocabulary (user-facing):** **Captain** = the business owner, **Ship** = the A-hoy app, **Crew** = the A-hoy team on the Crew Deck. Code, API paths and tables keep "client" for the business account (no rename). Direct address ("you") is fine inside the Ship; labels, statuses and every SMS/push name the Captain and use Ship words (Manifest, Radar, "awaiting your mark", "stay in port"). Guarded by `test_captain_notifications_are_on_theme`. (0.14.0)
- **Audit log is automatic.** A SQLAlchemy `before_flush` hook writes an `audit_events` row for every post `status` and review `reply_status` change (and creation), from any path — API, worker, webhook. The actor comes from a context variable set when the bearer token is verified; jobs record `system`, Stripe `webhook`. Integration credential saves are logged with field **names only**. (0.15.0)
- **Observability:** `LOG_FORMAT=json` for one-JSON-object-per-line logs; Sentry (API, worker job failures, web) only when a DSN is set, with `send_default_pii=False` so Captains' phones/emails stay out. One `app.__version__` feeds FastAPI's version and the Sentry release. (0.15.0)
- **PRD §7 KPIs in-app** (`services/kpis.py`, `GET /kpis`, Crew Deck panel): time-to-approve = Crew release → Captain approval (from the audit log), share under 48h, Captain active in 30 days (session or Ship action), logo churn from Stripe status. Crew fulfillment minutes and gross margin aren't recorded by the platform. (1.0.0)
- **1.0.0 = Milestone D code-complete**, per the iterations rule (major bump for a milestone). The pilot itself is an operations step tracked by D14. (1.0.0)
---

## Change log

### 2026-11-01

- 1.0.0: Milestone D code-complete — KPI tooling (D14), integrations setup guide, plan/README refresh, Phase 1 coverage table. Pilot rollout pending.
- 0.15.0: D13 shipped (automatic audit log + Crew "Ship's log", Sentry for API/worker/web, JSON logs).
- 0.14.0: D15 terminology sweep (Captain / Ship / Crew) across Ship, Crew Deck, SMS/push copy and Milestone D docs.
- 0.13.0: D11 shipped (Stripe Checkout / portal / webhooks ↔ tier + billing period, ad-spend pass-through). Terminology sweep scheduled as 0.14.0; D13 → 0.15.0.
- 0.12.0: D12 shipped (Ship client switcher — BUG-004, voice-note edit requests, swipe-to-approve, PWA manifest + service worker + FCM web push). 0.12 split into 0.12/0.13/0.14.
- 0.11.0: D10 shipped (Google/Facebook/Yelp review sync, real reply posting, per-client auto-reply delay, Captain edit/skip/send-now, GBP performance → Detailed View). BUG-005 found + fixed.
- 0.10.0: D9 shipped (Twilio call tracking + form leads → lead_events → hourly rollup; itemized revenue breakdown with recordings; Detailed View; Crew wiring + manual metrics).
- 0.9.0: D7–D8 shipped (background worker, Ayrshare auto-publish, encrypted integration credentials, Crew client settings, Ship Logbook).
- 0.8.0: D5–D6 shipped (real notification dispatch + log, 48h queue deep link, queue expiry + 48h reminder, low-star alert). BUG-002, BUG-003 fixed.
- 0.7.0: D1–D4 shipped (ROI correctness, full Brand Brain context, multi-channel fan-out + SEO/hashtags + AI tagging, Crew "Needs crew" + caption edit). BUG-001 fixed. CI now runs DB tests against a pgvector service.
- Milestone D opened from the Phase 1 PRD audit; bug log created with BUG-001..004.
