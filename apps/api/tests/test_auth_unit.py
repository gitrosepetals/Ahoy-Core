from app.services.auth import hash_token


def test_hash_token_is_stable_sha256() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abcd")
    assert len(hash_token("abc")) == 64
