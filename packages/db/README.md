# Database package

SQL migrations and seeds for A-hoy (Postgres + `pgvector`).

## Migrations

| File | Purpose |
|---|---|
| `migrations/001_initial_schema.sql` | Core schema with `captain`/`crew`/`deckhand`/`admin`, plus auth, push tokens, reviews, leads, credentials |
| `migrations/002_seed_oak_lawn.sql` | Demo tenant Oak Lawn Optometry |

Apply (libpq URL, not the SQLAlchemy async URL):

```bash
psql "$DATABASE_URL_PSQL" -f packages/db/migrations/001_initial_schema.sql
psql "$DATABASE_URL_PSQL" -f packages/db/migrations/002_seed_oak_lawn.sql
```

Or start `docker compose up -d db` (runs both scripts on first boot).

The root file `a_hoy_postgresql_database_schema.sql` is the original PRD draft; **Milestone A uses `packages/db/migrations/` as source of truth**.
