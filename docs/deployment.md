# Deployment (Vercel + Railway + Supabase)

Stack and why: see [technical_implementation_plan.md](./technical_implementation_plan.md). Vendor keys (Twilio, Stripe, OpenAI, …) are in [integrations_setup.md](./integrations_setup.md). Local Docker is for development only — never ship the `db` container.

| Piece | Host | Notes |
|---|---|---|
| Web (Next.js, `apps/web`) | Vercel | Root directory `apps/web` |
| API (FastAPI) | Railway service #1 | Dockerfile in `apps/api` |
| Worker (`python -m app.worker`) | Railway service #2 | Same image, different start command |
| Postgres + pgvector | Supabase | |
| Media + voice notes | Supabase Storage | Public bucket, `STORAGE_BACKEND=supabase` |

Keep **two environments**: staging (separate Supabase project, Stripe/Twilio test mode) and production. Do staging first, end to end.

## 1. Supabase

1. Create a project. Database → Extensions → enable **vector**.
2. Apply every `packages/db/migrations/*.sql` in filename order (SQL editor, or `psql "$DATABASE_URL_PSQL" -f …`). Seed files only on staging.
3. Storage → new **public** bucket named `ahoy-media`.
4. Collect: project URL, `service_role` key (server-side only — never in the web app), and the Postgres connection string. Use the **direct** or **session-mode** string (port 5432). The transaction pooler (6543) breaks asyncpg prepared statements.
   - API `DATABASE_URL` = `postgresql+asyncpg://postgres:<pw>@<host>:5432/postgres`

## 2. Railway (API + worker)

1. New project → deploy from the GitHub repo. Service **api**: root directory `apps/api` (it picks up the `Dockerfile`). Add a public domain, or a custom one like `api.yourdomain.com`.
2. Second service **worker**: same repo and root directory; set the start command to `python -m app.worker`. (For a very small first pilot you can skip it and set `EMBEDDED_WORKER=true` on the api instead — but then a restart interrupts jobs and you must run only **one** api instance.)
3. Set variables on **both** services (use Railway shared variables):

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase string above |
| `JWT_SECRET` | long random string (`openssl rand -hex 32`) |
| `CREDENTIALS_ENCRYPTION_KEY` | long random string. **Back it up** — losing it makes stored client credentials unreadable |
| `AUTH_DEV_MODE` | `false` (otherwise magic links are shown on screen, not sent) |
| `LLM_DEV_MODE` | `false` (needs `OPENAI_API_KEY`) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | real SMS for magic links |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET` | from step 1 |
| `PUBLIC_API_BASE_URL` | the API's public URL |
| `SHIP_APP_BASE_URL`, `CREW_APP_BASE_URL` | the web app's public URL (used in SMS links) |
| `CORS_ORIGINS` | the web origin exactly, e.g. `https://app.yourdomain.com` (add `capacitor://localhost` for the mobile shell) |
| `LOG_FORMAT` | `json` |
| `SENTRY_DSN` | optional but recommended |
| Stripe / Ayrshare / Google / Yelp / FCM keys | per [integrations_setup.md](./integrations_setup.md) |

4. Check `https://<api-domain>/health` returns `{"status":"ok"}`.

## 3. Vercel (web)

1. Import the repo; set **Root Directory** to `apps/web`.
2. Env var: `NEXT_PUBLIC_API_BASE_URL=https://<api-domain>/api/v1` (plus the `NEXT_PUBLIC_FIREBASE_*` / Sentry vars you use locally).
3. `NEXT_PUBLIC_*` values are baked in at build time — **redeploy after changing them**.
4. Add your custom domain, then put it in the API's `CORS_ORIGINS`, `SHIP_APP_BASE_URL` and `CREW_APP_BASE_URL`.

## 4. Webhooks

Point these at the API's public URL (not localhost):
- Stripe → `https://<api-domain>/api/v1/webhooks/stripe` (use the live `whsec_…`)
- Twilio voice → per client, shown in Crew → Client settings
- Google OAuth redirect → `https://<api-domain>/api/v1/integrations/google/callback` (register it in Google Cloud and set `GOOGLE_REDIRECT_URI` to match)

## 5. Go-live checklist

- [ ] Staging passes the full flow: sign in by real SMS, upload a photo, generate, approve, publish
- [ ] `AUTH_DEV_MODE=false`, `LLM_DEV_MODE=false`, secrets are not the dev defaults
- [ ] Uploaded photo URL starts with `https://<project>.supabase.co/storage/…` and survives an API redeploy
- [ ] Worker service running (check logs for the scheduler ticks); only one worker
- [ ] Supabase backups on (paid plan gives daily backups; free does not — upgrade before real customer data)
- [ ] Stripe webhook delivering (Stripe dashboard → recent deliveries all 2xx)
- [ ] Sentry receiving a test error
- [ ] Per-client checklist in [integrations_setup.md](./integrations_setup.md)

## Known limits

- The bucket is **public**: files are unguessable (UUID names) but not access-controlled. Fine for marketing photos; voice notes are also in it. Move to signed URLs before storing anything sensitive.
- Run **one** API instance while `EMBEDDED_WORKER=true`.
- Do not run `docker compose` services in production; managed Postgres handles backups and upgrades.
