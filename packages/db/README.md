# Database package

SQL migrations and seeds for A-hoy (Postgres + `pgvector`).

## Migrations

| File | Purpose |
|---|---|
| `migrations/001_initial_schema.sql` | Core schema with `captain`/`crew`/`deckhand`/`admin`, plus auth, push tokens, reviews, leads, credentials |
| `migrations/002_seed_oak_lawn.sql` | Demo tenant Oak Lawn Optometry |
| `migrations/003_seed_oak_lawn_media.sql` | Placeholder media for Oak Lawn |
| `migrations/004_seed_oak_lawn_reviews.sql` | Seeded Google reviews for Oak Lawn |
| `migrations/005_marketing_leads.sql` | Welcome-page email capture (`marketing_leads`) |
| `migrations/006_brand_brain_billing_period.sql` | 0.7.0 — Brand Brain pricing / seasonal offers / SEO keywords; `clients.billing_anchor_day` |
| `migrations/007_notifications_queue_expiry.sql` | 0.8.0 — `notifications` log, `approval_status.expired`, queue `released_at` / `reminder_sent_at`, `reviews.alerted_at` |
| `migrations/008_lead_tracking.sql` | 0.10.0 — call forwarding / recording / form key / timezone on `clients`; idempotent `lead_events`; `impressions` / `clicks` |
| `migrations/009_review_sync.sql` | 0.11.0 — `reply_status.scheduled`, reply due/posted/error/target on `reviews`; `auto_reply_delay_hours`, Facebook page, Yelp business on `clients` |
| `migrations/010_stripe_billing.sql` | 0.13.0 — Stripe customer / subscription / status / period end on `clients`; `stripe_events` idempotency |
| `migrations/011_audit_log.sql` | 0.15.0 — `audit_events` (status transitions, credential saves, billing changes) |

Apply (libpq URL, not the SQLAlchemy async URL):

```bash
psql "$DATABASE_URL_PSQL" -f packages/db/migrations/001_initial_schema.sql
psql "$DATABASE_URL_PSQL" -f packages/db/migrations/002_seed_oak_lawn.sql
```

Or start `docker compose up -d db` — every file in `migrations/` runs in order on **first boot of an empty volume**. On an existing volume apply new files by hand:

```bash
docker exec -i ahoymarketingplatform-db-1 psql -U postgres -d ahoy -v ON_ERROR_STOP=1 < packages/db/migrations/006_brand_brain_billing_period.sql
```

CI applies all migrations to a fresh pgvector service before running pytest.

The root file `a_hoy_postgresql_database_schema.sql` is the original PRD draft; **Milestone A uses `packages/db/migrations/` as source of truth**.
