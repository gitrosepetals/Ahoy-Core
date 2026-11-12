# Integrations setup

Vendor-side setup for every provider the platform talks to, which env vars each one needs, what Crew enters per client, and how to verify it end to end. Everything here is **optional locally**: without credentials each integration runs in dev mode (logged / faked) so the full Captain ↔ Crew flow still works.

Env vars live in `apps/api/.env` (API + worker) and `apps/web/.env.local` (web); the full list with comments is in [`.env.example`](../.env.example). Design rationale and gotchas are in [milestone_d.md § Design decisions](./milestone_d.md#design-decisions).

**Before any webhook-based provider** (Twilio, Stripe, Google OAuth): the API must be reachable from the internet at `PUBLIC_API_BASE_URL` — in production your API host, locally a tunnel (e.g. `ngrok http 8000`, then set `PUBLIC_API_BASE_URL=https://<id>.ngrok.app`). Run the worker too (`uv run python -m app.worker`, or `EMBEDDED_WORKER=true`).

| Provider | Powers | PRD |
|---|---|---|
| [Twilio](#twilio) | Sign-in links, Captain SMS alerts, call tracking + recordings | 1.1, CL-01, CL-02, CL-05 |
| [Firebase (FCM)](#firebase-cloud-messaging) | Push to the Ship (PWA + native) | CL-02, CL-05 |
| [OpenAI](#openai) | Captions, revisions, review replies, photo tags, voice-note transcription, Brand Brain embedding | AG-01, AG-03, 1.2 |
| [Ayrshare](#ayrshare) | Auto-publishing to Instagram, Facebook, TikTok, Google | CL-02 |
| [Google Business Profile](#google-business-profile) | Google reviews + replies, impressions / clicks / directions | CL-05, CL-01 |
| [Facebook Page](#facebook-page) | Facebook recommendations + replies | CL-05 |
| [Yelp](#yelp) | Yelp review excerpts (read-only) | CL-05 |
| [Stripe](#stripe) | Subscriptions, customer portal, ad-spend pass-through | §4 |
| [Sentry](#sentry) | Error alerts (API, worker, web) | — |

---

## Twilio

**Vendor side**
1. Create a Twilio account; upgrade it (trial accounts can only text verified numbers).
2. **Messaging number** (sends sign-in links + alerts): buy one local number. For US A2P SMS, register a brand + campaign (A2P 10DLC) — carriers block unregistered traffic.
3. **Tracking numbers**: buy **one local number per client** (ideally in the client's area code). For each: *Phone Numbers → Manage → Active numbers → (number) → Voice Configuration*:
   - A call comes in → **Webhook**, `POST`, URL = the "Twilio Voice webhook" shown in Crew → Client settings (`{PUBLIC_API_BASE_URL}/api/v1/webhooks/twilio/voice`).
4. Recordings: *Voice → Settings → General* — keep **HTTP Basic Authentication for media access** enabled (the API proxies playback with your account credentials).

**Env:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (messaging number, E.164), `AUTH_DEV_MODE=false` (until this is false nothing is sent and webhook signatures aren't enforced), `PUBLIC_API_BASE_URL` (must match exactly what Twilio calls — signatures are computed over it).

**Per client (Crew → Client settings):** Twilio tracking number, Forward tracked calls to (the business's real line), Record tracked calls (callers hear a recording notice — Illinois is all-party consent), Timezone.

**Verify**
- Sign-in: request a link on `/auth/sign-in` → SMS arrives.
- Call the tracking number for over 60s → it rings the business; run `uv run python -m app.worker --once` → Ship Treasure Map → tap revenue → the call is listed as "counted" with ▶ Play recording.
- Wrong `PUBLIC_API_BASE_URL` shows up as `403 Bad Twilio signature` in the Twilio debugger.

## Firebase Cloud Messaging

**Vendor side**
1. Create a Firebase project.
2. *Project settings → Service accounts → Generate new private key* → save the JSON on the API host (never commit it).
3. *Project settings → General → Your apps → Add app (Web)* → copy the config object.
4. *Project settings → Cloud Messaging → Web Push certificates → Generate key pair* → copy the public key (VAPID).
5. Native builds (Capacitor): add iOS/Android apps in the same project (APNs key for iOS).

**Env:** API `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_FILE` (path to the JSON). Web `NEXT_PUBLIC_FIREBASE_CONFIG` (the config as one-line JSON), `NEXT_PUBLIC_FIREBASE_VAPID_KEY`.

**Verify:** Captain → Ship Map → **Turn on Ship alerts** → allow → message "Notifications on". Crew releases a batch → push arrives; Crew → Captain notifications shows `queue_ready · push · sent`. Without FCM the same row says `sms` or `log`.

## OpenAI

**Vendor side:** create an API key in a project with access to the chat model (`gpt-4o-mini` default), `text-embedding-3-small` and `whisper-1`.

**Env:** `OPENAI_API_KEY`, `LLM_DEV_MODE=false`, optionally `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL`.

**Verify:** Crew → Generate drafts → captions no longer start with `[DEV]`; upload a photo → tags like `staff, smiling team` instead of filename hints; Captain voice note → caption rewritten from what was said.

## Ayrshare

**Vendor side**
1. Create an Ayrshare account on the **Business** plan (needed for multiple client profiles).
2. For each client: *Profiles → Create profile* → copy the **Profile Key**.
3. Have the Captain link their socials to that profile (Ayrshare's social-linking page / "Generate JWT" link): Instagram (Business/Creator account connected to a Facebook Page), Facebook Page, TikTok, Google Business Profile.

**Env:** `AYRSHARE_API_KEY` (account API key), `PUBLIC_API_BASE_URL` reachable publicly — Ayrshare downloads media from the vault URLs (local `uploads/` on localhost won't work).

**Per client:** Crew → Client settings → Ayrshare profile key → Save key (stored encrypted, never shown again).

**Verify:** approve a post with a photo, wait for its time (or set it a minute out), run the worker → Crew Approved tab shows **Published**, Ship Logbook shows "Sailed ✓", the post is live. Failures show "Retrying: <reason>" then "Publish failed" with Retry / Mark sent. Email/SMS channels always show "Send manually" (no email/SMS sender yet).

## Google Business Profile

**Vendor side**
1. Google Cloud project → enable **My Business Account Management API**, **My Business Business Information API**, **Business Profile Performance API**, and the legacy **Google My Business API** (v4 — reviews). These are gated: submit Google's **Business Profile API access request** form for the project and wait for approval (quota is 0 until then).
2. *APIs & Services → OAuth consent screen*: External, scope `https://www.googleapis.com/auth/business.manage`; add pilot Captains as test users until the app is verified.
3. *Credentials → Create OAuth client ID (Web application)* → Authorized redirect URI = `{PUBLIC_API_BASE_URL}/api/v1/integrations/google/callback`.

**Env:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` (exactly the registered URI), `CREW_APP_BASE_URL` (where the callback sends Crew back).

**Per client:** Crew → **Connect Google (Captain signs in)** with the Captain present (they sign in with the Google account that manages the listing) → **Choose location** → Save client settings.

**Verify:** Crew → **Sync reviews now** → reviews appear in the Ship Radar; a new 5★ shows "Auto-reply posts <time>"; Send now → reply visible on Google. Next 6-hourly run fills impressions / clicks / directions (Ship → Detailed view).

## Facebook Page

**Vendor side**
1. Meta for Developers → create an app (type Business); add the Captain's Page admin as a tester or complete App Review for: `pages_show_list`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_engagement`.
2. Graph API Explorer (as the Page admin) → user token with those permissions → exchange for a **long-lived** user token → `GET /me/accounts` → copy that Page's **access_token** (long-lived Page token) and **id**.

**Env:** none (token is per client).

**Per client:** Crew → Facebook Page → Page id + long-lived Page access token → Save Facebook.

**Verify:** Sync reviews now → Facebook recommendations appear (recommend → 5★, don't recommend → 2★); approving a reply posts it as a comment on the recommendation.

## Yelp

**Vendor side:** create an app at Yelp Fusion → copy the API key. Find the business id (the slug in the business's Yelp URL or via the Business Search endpoint).

**Env:** `YELP_API_KEY`.

**Per client:** Crew → Client settings → Yelp business id → Save.

**Verify:** Sync reviews now → up to 3 most recent Yelp excerpts appear. Yelp has no reply API: the Ship shows **Copy reply** for the Captain to paste on Yelp.

## Stripe

**Vendor side**
1. *Products*: create **Harbor**, **Cruiser**, **Flagship**, each with a monthly recurring price → copy the three **price ids**.
2. *Developers → Webhooks → Add endpoint*: `{PUBLIC_API_BASE_URL}/api/v1/webhooks/stripe`, events `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed` → copy the signing secret.
3. *Settings → Billing → Customer portal*: activate; allow payment-method updates, invoice history, cancellation (and plan switching between the three prices if desired).

**Env:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_HARBOR`, `STRIPE_PRICE_CRUISER`, `STRIPE_PRICE_FLAGSHIP`.

**Local:** `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe` and use the `whsec_…` it prints.

**Verify:** Crew → Billing → choose tier → **Create checkout link** → pay with `4242 4242 4242 4242` → Crew and Ship show the tier, `active` and renewal date; Ship → **Manage billing** opens the portal; Crew → **Bill ad spend** adds a line to the next invoice; the Treasure Map's billing period now starts on Stripe's cycle day.

## Sentry

**Vendor side:** create two projects (Python/FastAPI and Browser JavaScript) → copy each DSN.

**Env:** API `SENTRY_DSN`, optional `SENTRY_TRACES_SAMPLE_RATE`; web `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT`. Also set `LOG_FORMAT=json` in production.

**Verify:** raise a test error (e.g. stop Postgres and run `python -m app.worker --once`) → event in Sentry tagged `component=worker`, release `ahoy-api@<version>`. No PII is sent.

---

## Go-live checklist (per pilot client)

1. Crew → Client settings: tracking number, forward-to number, timezone, billing day (until Stripe sets it), auto-reply delay.
2. Twilio number Voice URL set; test call counted.
3. Website form pointed at the client's form URL (shown in Client settings); test submission listed.
4. Google connected + location chosen; Facebook / Yelp if used; first sync done.
5. Ayrshare profile linked to the Captain's socials; profile key saved; one test post published.
6. Captain signed in once on their phone, **Turn on Ship alerts**, added the Ship to the home screen.
7. Stripe checkout completed.
