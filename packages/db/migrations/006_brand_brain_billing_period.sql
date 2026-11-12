-- 0.7.0 — Phase 1 gaps: Brand Brain fields (AG-01) + billing period anchor (CL-01 / Story 2.1)

-- AG-01: pricing, seasonal offers and local SEO keywords live in their own fields
-- instead of being stuffed into free-form services JSON.
ALTER TABLE brand_profiles
    ADD COLUMN IF NOT EXISTS pricing_notes TEXT,
    ADD COLUMN IF NOT EXISTS seasonal_offers JSONB,
    ADD COLUMN IF NOT EXISTS local_seo_keywords TEXT[];

-- Story 2.1: revenue is shown "for the current billing period". Day of month the
-- period starts (Stripe billing_cycle_anchor day once billing lands). 1..28 avoids short months.
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS billing_anchor_day SMALLINT NOT NULL DEFAULT 1
        CHECK (billing_anchor_day BETWEEN 1 AND 28);

-- Demo tenant values
UPDATE brand_profiles
SET pricing_notes = 'Exams from $150; contact lens fitting $75; complete frames + lenses from $199. FSA/HSA accepted.',
    seasonal_offers = '[{"name":"Use-it-or-lose-it FSA","window":"Nov-Dec","detail":"FSA dollars expire Dec 31 - book an exam or new frames"},{"name":"Back-to-school eye exams","window":"Jul-Aug","detail":"Kids exams before the school year"}]'::jsonb,
    local_seo_keywords = ARRAY['Oak Lawn eye doctor', 'optometrist near me', 'eye exam Oak Lawn IL']
WHERE client_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
  AND pricing_notes IS NULL;
