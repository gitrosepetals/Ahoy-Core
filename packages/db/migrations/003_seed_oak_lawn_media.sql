-- Sample media for Oak Lawn so campaign generate works before first upload
INSERT INTO media_assets (
    asset_id,
    client_id,
    storage_url,
    thumbnail_url,
    asset_type,
    ai_tags
) VALUES
    (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'https://placehold.co/1080x1350/0c4a6e/white?text=Oak+Lawn+Frames',
        'https://placehold.co/400x500/0c4a6e/white?text=Frames',
        'raw_photo',
        ARRAY['eyewear_display', 'product']
    ),
    (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'https://placehold.co/1080x1920/075985/white?text=Dr+Nguyen',
        'https://placehold.co/400x700/075985/white?text=Staff',
        'raw_photo',
        ARRAY['staff_intro', 'exam_room']
    )
ON CONFLICT (asset_id) DO NOTHING;
