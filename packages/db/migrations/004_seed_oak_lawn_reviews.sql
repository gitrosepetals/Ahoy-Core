-- Seeded Google reviews for Oak Lawn Reputation Radar (Milestone C)
INSERT INTO reviews (
    review_id,
    client_id,
    provider,
    external_id,
    rating,
    body,
    reviewer_name,
    ai_reply,
    reply_status,
    reviewed_at
) VALUES
    (
        'cccccccc-cccc-cccc-cccc-ccccccccccc1',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'google',
        'gbp-seed-5star-1',
        5,
        'Dr. Nguyen and the team are wonderful. Fast exam, great frame selection.',
        'Maria S.',
        '[DEV] Thank you so much, Maria! We are glad your visit went smoothly. — Oak Lawn Optometry',
        'auto_sent',
        NOW() - INTERVAL '3 days'
    ),
    (
        'cccccccc-cccc-cccc-cccc-ccccccccccc2',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'google',
        'gbp-seed-4star-1',
        4,
        'Solid experience. Parking was a little tight but the staff was kind.',
        'James T.',
        '[DEV] Thanks James — we appreciate the note about parking and are glad the team took care of you.',
        'auto_sent',
        NOW() - INTERVAL '2 days'
    ),
    (
        'cccccccc-cccc-cccc-cccc-ccccccccccc3',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'google',
        'gbp-seed-2star-1',
        2,
        'Waited longer than expected and felt rushed at the end.',
        'Alex R.',
        '[DEV] Alex, we are sorry the visit felt rushed. We would like to make this right — please call us so we can help.',
        'awaiting_captain',
        NOW() - INTERVAL '1 day'
    )
ON CONFLICT (client_id, provider, external_id) DO NOTHING;
