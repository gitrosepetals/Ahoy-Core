-- Seed demo tenant: Oak Lawn Optometry (Captain + Crew)
-- Fixed UUIDs for local/dev predictability

INSERT INTO users (user_id, email, full_name, phone_number, role) VALUES
    ('11111111-1111-1111-1111-111111111111', 'dr.nguyen@oaklawnoptometry.example', 'Dr. Mai Nguyen', '+15551234001', 'captain'),
    ('22222222-2222-2222-2222-222222222222', 'jordan@ahoy.example', 'Jordan Blake', '+15551234002', 'crew'),
    ('33333333-3333-3333-3333-333333333333', 'admin@ahoy.example', 'A-hoy Admin', '+15551234000', 'admin');

INSERT INTO clients (
    client_id,
    business_name,
    industry_vertical,
    tier,
    owner_user_id,
    assigned_crew_id,
    average_ticket_value,
    conversion_rate_estimate
) VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'Oak Lawn Optometry',
    'Optometry',
    'cruiser',
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    280.00,
    0.25
);

INSERT INTO brand_profiles (
    client_id,
    brand_voice_guidelines,
    target_zip_codes,
    compliance_rules,
    services_offered
) VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'Warm, clinical yet accessible, neighborhood-focused. Speak like a trusted local doctor, not a big-box chain.',
    ARRAY['60453', '60455', '60459'],
    'No guaranteed medical outcomes; include Illinois optometry disclaimer where clinical claims appear. Avoid before/after vision guarantees.',
    '{"services":[{"name":"Comprehensive eye exam","price":150},{"name":"Contact lens fitting","price":75},{"name":"Complete pair frames + lenses","from":199}]}'::jsonb
);

INSERT INTO daily_roi_metrics (
    client_id,
    metric_date,
    tracked_calls_count,
    form_leads_count,
    new_reviews_count,
    ad_spend_usd
) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', CURRENT_DATE - 2, 4, 2, 1, 45.00),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', CURRENT_DATE - 1, 6, 1, 0, 52.00),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', CURRENT_DATE, 3, 2, 2, 48.00);
